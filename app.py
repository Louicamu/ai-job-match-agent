"""
AI 求职智能匹配与简历优化智能体
===================================
基于 Streamlit + Supabase + LLM 的全栈 AI 求职助手。
QQ邮箱免密登录 | AI岗位匹配 | STAR法则简历优化 | 云端历史回放
"""

import streamlit as st
import json
import random
import time
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# ─── Optional Supabase ───────────────────────────────────────────────
try:
    from supabase import create_client, Client
    SUPA_AVAILABLE = True
except ImportError:
    SUPA_AVAILABLE = False

# ─── Optional OpenAI-compatible LLM ───────────────────────────────────
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# ======================================================================
# PAGE CONFIGURATION
# ======================================================================
st.set_page_config(
    page_title="AI 求职智能匹配 · 简历优化智能体",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================================
# GLOBAL CONSTANTS
# ======================================================================
VERIFICATION_CODE_EXPIRY = 300  # 5 minutes in seconds
JOBS_DB_PATH = Path(__file__).parent / "jobs_db.json"


# ======================================================================
# HELPER: Load secrets safely
# ======================================================================
def get_secret(section: str, key: str) -> Optional[str]:
    """Safely read a nested secret from st.secrets with graceful fallback."""
    try:
        return st.secrets[section][key]
    except (KeyError, TypeError):
        return None


# ======================================================================
# HELPER: Load jobs database
# ======================================================================
@st.cache_data(show_spinner=False)
def load_jobs_db() -> List[Dict[str, Any]]:
    """Load the mock job database from local JSON file."""
    try:
        with open(JOBS_DB_PATH, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        return jobs
    except Exception as e:
        st.error(f"❌ 无法加载岗位数据库: {e}")
        return []


# ======================================================================
# HELPER: Format jobs summary for LLM prompt
# ======================================================================
def format_jobs_for_prompt(jobs: List[Dict[str, Any]]) -> str:
    """Convert jobs list into a concise prompt-friendly text block."""
    lines = []
    for job in jobs:
        lines.append(
            f"【岗位ID: {job['id']}】{job['title']} @ {job['company']}（{job['location']}）\n"
            f"  薪资: {job['salary']}\n"
            f"  岗位职责: {job['jd']}\n"
            f"  任职要求: {job['requirements']}\n"
        )
    return "\n".join(lines)


# ======================================================================
# HELPER: Validate email format
# ======================================================================
def is_valid_qq_email(email: str) -> bool:
    """Check if the email is a valid QQ email address."""
    pattern = r"^[1-9]\d{4,10}@qq\.com$"
    return bool(re.match(pattern, email))


# ======================================================================
# HELPER: Generate verification code
# ======================================================================
def generate_verification_code() -> str:
    """Generate a 6-digit random verification code."""
    return "".join([str(random.randint(0, 9)) for _ in range(6)])


# ======================================================================
# SMTP: Send verification email via QQ Mail
# ======================================================================
def send_verification_email(to_email: str, code: str) -> tuple[bool, str]:
    """
    Send a 6-digit verification code to the user's QQ email via SMTP SSL.
    Returns (success: bool, message: str).
    """
    sender = get_secret("qq_mail", "sender")
    auth_code = get_secret("qq_mail", "auth_code")

    if not sender or not auth_code:
        return False, "QQ邮箱配置缺失，请联系管理员在 secrets 中配置 [qq_mail]"

    # ── Build HTML email ──────────────────────────────────────────────
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6fb;font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fb;padding:40px 0;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.08);overflow:hidden;">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#667eea,#764ba2);padding:32px 40px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">🎯 AI 求职智能体</h1>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">您的专属求职匹配与简历优化助手</p>
  </td></tr>

  <!-- Body -->
  <tr><td style="padding:36px 40px;">
    <p style="color:#333;font-size:15px;margin:0 0 8px;">您好，</p>
    <p style="color:#555;font-size:14px;line-height:1.8;margin:0 0 24px;">
      您正在进行邮箱验证登录。<br>
      请在 <strong>5 分钟</strong>内使用以下验证码完成验证：
    </p>

    <!-- Code Box -->
    <div style="background:#f8f9fc;border:2px dashed #667eea;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
      <span style="font-size:36px;font-weight:800;letter-spacing:10px;color:#667eea;font-family:'SF Mono','Menlo','Consolas',monospace;">{code}</span>
    </div>

    <p style="color:#999;font-size:12px;margin:0 0 24px;line-height:1.6;">
      ⏰ 验证码有效期 5 分钟，过期需重新获取<br>
      🔒 如非本人操作，请忽略此邮件
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:0 0 20px;">
    <p style="color:#bbb;font-size:11px;text-align:center;margin:0;">
      AI 求职智能匹配与简历优化智能体 · 安全登录验证
    </p>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🎯 AI求职智能体 - 登录验证码"
    msg["From"] = f"AI求职智能体 <{sender}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # ── Connect & Send via SSL ────────────────────────────────────────
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context, timeout=15) as server:
            server.login(sender, auth_code)
            server.sendmail(sender, to_email, msg.as_string())
        return True, "验证码已发送，请查收QQ邮箱"
    except smtplib.SMTPAuthenticationError:
        return False, "QQ邮箱SMTP认证失败，请检查授权码是否正确"
    except smtplib.SMTPConnectError:
        return False, "无法连接到QQ邮箱SMTP服务器(smtp.qq.com:465)，请检查网络"
    except smtplib.SMTPException as e:
        return False, f"邮件发送异常: {e}"
    except Exception as e:
        return False, f"未知错误: {e}"


# ======================================================================
# SUPABASE: Initialize client
# ======================================================================
@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Optional[Client]:
    """Initialize and return a cached Supabase client."""
    if not SUPA_AVAILABLE:
        return None
    url = get_secret("supabase", "url")
    anon_key = get_secret("supabase", "anon_key")
    if not url or not anon_key:
        return None
    try:
        return create_client(url, anon_key)
    except Exception:
        return None


# ======================================================================
# SUPABASE: Ensure user exists (insert if new)
# ======================================================================
def ensure_user_exists(supabase: Client, email: str) -> bool:
    """Check if user exists in `users` table; insert if not. Returns True on success."""
    try:
        supabase.table("users").upsert({"email": email}).execute()
        return True
    except Exception as e:
        st.warning(f"⚠️ 用户注册/登录记录写入失败: {e}")
        return False


# ======================================================================
# SUPABASE: Save diagnosis history
# ======================================================================
def save_diagnosis_history(
    supabase: Client,
    user_email: str,
    resume_text: str,
    matched_jobs: List[Dict],
    optimization_advice: str,
) -> bool:
    """Insert a new diagnosis record into the `history` table."""
    try:
        payload = {
            "user_email": user_email,
            "resume_text": resume_text,
            "matched_jobs": json.dumps(matched_jobs, ensure_ascii=False),
            "optimization_advice": optimization_advice,
        }
        supabase.table("history").insert(payload).execute()
        return True
    except Exception as e:
        st.warning(f"⚠️ 历史记录保存失败: {e}")
        return False


# ======================================================================
# SUPABASE: Fetch user history
# ======================================================================
def fetch_user_history(supabase: Client, user_email: str) -> List[Dict]:
    """Fetch diagnosis history for a user, ordered by created_at DESC."""
    try:
        resp = (
            supabase.table("history")
            .select("*")
            .eq("user_email", user_email)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        st.warning(f"⚠️ 历史记录加载失败: {e}")
        return []

# ======================================================================
# LLM: Initialize OpenAI-compatible client
# ======================================================================
@st.cache_resource(show_spinner=False)
def get_llm_client() -> Optional[OpenAI]:
    """Initialize and return a cached LLM client."""
    if not LLM_AVAILABLE:
        return None
    api_key = get_secret("llm", "api_key")
    base_url = get_secret("llm", "base_url")
    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key, base_url=base_url or None)
    except Exception:
        return None


def get_model_name() -> str:
    """Return configured model name, with fallback."""
    return get_secret("llm", "model_name") or "gpt-4o-mini"


# ======================================================================
# LLM: STEP A — Job Matching
# ======================================================================
def llm_job_matching(client: OpenAI, resume: str, jobs: List[Dict]) -> Optional[List[Dict]]:
    """
    Match user's resume against the job database.
    Returns top 3 jobs with match percentage and reasoning.
    """
    model = get_model_name()
    jobs_text = format_jobs_for_prompt(jobs)

    system_prompt = """你是一位在互联网大厂有15年经验的资深招聘总监（HR Director），深谙校园招聘的选人标准。
你的任务是将候选人的简历与岗位数据库进行**语义级深度匹配**，而非简单的关键词检索。

请你：
1. 通读候选人的教育背景、项目经历、实习经历、技能栈
2. 逐一分析每个岗位的JD和任职要求
3. 基于**能力模型匹配**（技术栈覆盖度、项目经验相关性、综合素质匹配度）给出综合评分
4. 选出 **Top 3 最匹配岗位**，每个岗位给出 0-100 的匹配百分比

**重要输出格式要求 —— 你必须严格输出以下JSON格式，不要输出任何其他内容：**
```json
{
  "matches": [
    {
      "job_id": 1,
      "job_title": "岗位名",
      "company": "公司名",
      "match_score": 85,
      "match_reason": "详细匹配理由（100字以内）：说明候选人的哪些背景与该岗位高度契合",
      "gap_summary": "核心差距简述（50字以内）：候选人目前最欠缺什么"
    }
  ]
}
```

**评分标准**：
- 90-100：高度匹配，技术栈和项目经验完全对口
- 75-89：较好匹配，核心技能具备，有少量可弥补的差距
- 60-74：部分匹配，有2-3项关键技能缺失但可通过学习补足
- 40-59：勉强匹配，需要较大努力才能胜任
- 0-39：不匹配，方向差异过大
"""

    user_prompt = f"""以下是候选人的简历内容：
---
{resume}
---

以下是目前开放的校招岗位数据库：
---
{jobs_text}
---

请基于以上信息，严格按照系统指令中的JSON格式，输出 Top 3 最匹配岗位。"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
            timeout=120,
        )
        raw = response.choices[0].message.content.strip()

        # Try to extract JSON from possible markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        if json_match:
            raw = json_match.group(1).strip()

        result = json.loads(raw)
        matches = result.get("matches", [])[:3]
        return matches
    except json.JSONDecodeError as e:
        st.error(f"❌ AI返回格式解析失败，请重试。原始输出: {raw[:300]}...")
        return None
    except Exception as e:
        st.error(f"❌ AI岗位匹配请求失败: {e}")
        return None

# ======================================================================
# LLM: STEP B — Resume Optimization (STAR Method)
# ======================================================================
def llm_resume_optimization(
    client: OpenAI, resume: str, target_job: Dict
) -> Optional[str]:
    """
    Perform deep gap analysis and produce STAR-method optimization advice
    for the user's resume against a specific target job.
    """
    model = get_model_name()

    job_info = f"""【目标岗位】{target_job['title']}
【公司】{target_job['company']}
【部门】{target_job.get('department', 'N/A')}
【薪资范围】{target_job.get('salary', 'N/A')}
【岗位职责】{target_job['jd']}
【任职要求】{target_job['requirements']}"""

    system_prompt = """你是一位在腾讯/阿里巴巴/字节跳动等头部互联网公司有20年经验的**首席HR副总裁**，
专精于校招简历筛选与候选人辅导。你的诊断报告将直接影响候选人的求职成功率。

## 你的任务
对比候选人的简历与目标岗位的JD要求，输出一份**深度的、可操作的、专业的简历优化诊断报告**。

## 诊断报告结构要求（必须严格按以下顺序输出）

### 一、核心差距分析 🔍
以表格形式列出候选人与岗位要求之间最关键的 **3-5 个差距项**：
| 缺失技能/经验 | 重要性（高/中） | 当前状态 | 目标要求 |
|:---|:---|:---|:---|

### 二、简历关键词优化 🏷️
列出该岗位JD中**最核心的10个关键词**，标注候选人的简历目前是否覆盖：
- ✅ 已覆盖: xxx
- ❌ 需补充: xxx
- ⚠️ 部分覆盖: xxx

### 三、STAR法则修改范例 ⭐（最重要的部分）
针对每一个核心差距，你必须使用 **STAR 法则（Situation → Task → Action → Result）** 给出一段**可直接复制粘贴到简历中的修改范例**。

格式严格要求如下：
```
【差距项：XXX】
- S (情境): 描述一个具体的业务或技术场景...
- T (任务): 你需要完成的核心任务...
- A (行动): 你采取了哪些具体技术手段...
- R (结果): 用量化数据展示成果（必须包含具体数字，如性能提升X%、用户增长Y%、延迟降低Zms等）
```

### 四、综合评价与学习路线图 🗺️
- **当前竞争力评分**（0-100分，基于简历与JD匹配度）
- **提升到90分需要的行动**（按优先级排序，每条注明预计学习时间）
- **推荐突击准备的面试知识点**（按概率高低排序）

## 输出风格要求
- 专业但不冰冷，像一位资深导师在辅导学生
- 所有建议必须**具体、可执行**，拒绝空泛的套话
- 量化数据可以给出合理估算（标注"建议量化"）
- 使用 emoji 提升可读性，但不要过度
- 用粗体强调关键术语和技术名词
"""

    user_prompt = f"""我正在申请以下校招岗位，请帮我深度诊断并优化简历。

{job_info}

以下是我的简历内容：
---
{resume}
---

请严格按照系统指令中的结构要求，输出完整的诊断报告。特别注意：
1. STAR法则范例必须包含**具体的、可量化的结果数据**
2. 关键词覆盖分析要全面，不漏掉JD中的关键技术栈
3. 学习路线图要务实，考虑校招生的时间约束（毕业前通常有3-6个月准备时间）"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=8192,
            timeout=180,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ AI简历优化请求失败: {e}")
        return None

# ======================================================================
# SESSION STATE INITIALIZATION
# ======================================================================
def init_session_state():
    """Initialize all session state variables with safe defaults."""
    defaults = {
        # Auth state
        "is_logged_in": False,
        "user_email": "",
        "verification_code": "",
        "verification_code_time": 0.0,
        "verification_code_sent": False,
        # History
        "history_records": [],
        "selected_history_id": None,
        "selected_history_data": None,
        # AI diagnosis state
        "matched_jobs": [],
        "optimization_advice": "",
        "selected_job_id": None,
        "diagnosis_running": False,
        # UI state
        "resume_input": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ======================================================================
# UI COMPONENT: Sidebar — Authentication
# ======================================================================
def render_sidebar_auth():
    """Render the QQ email login/register panel in the sidebar."""
    st.sidebar.markdown("## 🔐 登录 / 注册")

    if st.session_state.is_logged_in:
        # ── Logged in state ───────────────────────────────────────────
        st.sidebar.success(f"✅ 已登录: {st.session_state.user_email}")
        if st.sidebar.button("🚪 退出登录", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return

    # ── Not logged in state ───────────────────────────────────────────
    email = st.sidebar.text_input(
        "📧 QQ邮箱地址",
        placeholder="例如: 123456789@qq.com",
        key="auth_email_input",
    )

    col1, col2 = st.sidebar.columns([1, 1])

    # Send code button
    with col1:
        if st.button("📨 发送验证码", use_container_width=True, disabled=not email):
            if not is_valid_qq_email(email):
                st.sidebar.error("❌ 请输入有效的QQ邮箱（数字@qq.com）")
            else:
                code = generate_verification_code()
                st.session_state.verification_code = code
                st.session_state.verification_code_time = time.time()
                st.session_state.verification_code_sent = True
                st.session_state.user_email = email

                with st.spinner("📧 正在发送验证码..."):
                    success, msg = send_verification_email(email, code)
                if success:
                    st.sidebar.success(f"✅ {msg}")
                else:
                    st.sidebar.error(f"❌ {msg}")
                    st.session_state.verification_code_sent = False

    # Verify code + login
    if st.session_state.verification_code_sent:
        st.sidebar.markdown("---")
        user_code = st.sidebar.text_input(
            "🔢 请输入6位验证码",
            max_chars=6,
            placeholder="000000",
            key="auth_code_input",
        )

        # Check expiry
        elapsed = time.time() - st.session_state.verification_code_time
        remaining = VERIFICATION_CODE_EXPIRY - int(elapsed)
        if remaining > 0:
            st.sidebar.caption(f"⏰ 验证码剩余有效时间: {remaining // 60}分{remaining % 60}秒")
        else:
            st.sidebar.warning("⚠️ 验证码已过期，请重新获取")
            st.session_state.verification_code_sent = False

        with col2:
            if st.button("✅ 确认登录", use_container_width=True, disabled=not user_code):
                if user_code != st.session_state.verification_code:
                    st.sidebar.error("❌ 验证码错误，请重新输入")
                elif elapsed > VERIFICATION_CODE_EXPIRY:
                    st.sidebar.warning("⚠️ 验证码已过期，请重新获取")
                    st.session_state.verification_code_sent = False
                else:
                    # Success — log in
                    st.session_state.is_logged_in = True
                    st.session_state.user_email = email

                    # Sync user to Supabase
                    supabase = get_supabase_client()
                    if supabase:
                        ensure_user_exists(supabase, email)
                    st.sidebar.success("🎉 登录成功！")
                    time.sleep(0.5)
                    st.rerun()


# ======================================================================
# UI COMPONENT: Sidebar — History
# ======================================================================
def render_sidebar_history():
    """Render diagnosis history list in the sidebar for logged-in users."""
    if not st.session_state.is_logged_in:
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📋 历史诊断记录")

    supabase = get_supabase_client()
    if not supabase:
        st.sidebar.info("ℹ️ Supabase 未配置，历史记录不可用")
        return

    # Fetch history
    records = fetch_user_history(supabase, st.session_state.user_email)
    st.session_state.history_records = records

    if not records:
        st.sidebar.caption("暂无诊断记录，快去试试吧 🚀")
        return

    st.sidebar.caption(f"共 {len(records)} 条记录")

    for i, record in enumerate(records):
        try:
            created_at = record.get("created_at", "")
            if created_at:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                time_label = dt.strftime("%m/%d %H:%M") if dt else "未知时间"
            else:
                time_label = "未知时间"

            resume_preview = (record.get("resume_text", "") or "")[:40].replace("\n", " ")
            label = f"🕐 {time_label} — {resume_preview}..."

            if st.sidebar.button(label, key=f"hist_{record['id']}", use_container_width=True):
                st.session_state.selected_history_id = record["id"]
                st.session_state.selected_history_data = record
                st.rerun()
        except Exception:
            continue

# ======================================================================
# UI COMPONENT: Main — History Playback
# ======================================================================
def render_history_playback():
    """If a history record is selected, display past diagnosis results."""
    data = st.session_state.selected_history_data
    if not data:
        return

    st.markdown("## 🔄 历史记录回放")

    col_hist, col_close = st.columns([10, 1])
    with col_hist:
        history_time = data.get("created_at", "未知")
        st.caption(f"📅 诊断时间: {history_time}")
    with col_close:
        if st.button("✕", key="close_history"):
            st.session_state.selected_history_id = None
            st.session_state.selected_history_data = None
            st.rerun()

    st.markdown("---")

    # Resume tab
    tab1, tab2, tab3 = st.tabs(["📄 原始简历", "🎯 匹配结果", "💡 优化建议"])

    with tab1:
        resume_text = data.get("resume_text", "") or ""
        st.text_area(
            "当时提交的简历内容",
            value=resume_text,
            height=300,
            disabled=True,
            key="history_resume",
            label_visibility="collapsed",
        )

    with tab2:
        matched_raw = data.get("matched_jobs", "[]") or "[]"
        try:
            matched_jobs = json.loads(matched_raw) if isinstance(matched_raw, str) else matched_raw
        except (json.JSONDecodeError, TypeError):
            matched_jobs = []
        if matched_jobs:
            for idx, job in enumerate(matched_jobs):
                score = job.get("match_score", 0)
                emoji = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
                with st.container(border=True):
                    st.markdown(f"### {emoji} Top {idx+1}: {job.get('job_title', '?')} @ {job.get('company', '?')}")
                    st.metric("匹配度", f"{score}%")
                    st.caption(f"**✅ 匹配理由**: {job.get('match_reason', 'N/A')}")
                    st.caption(f"**⚠️ 核心差距**: {job.get('gap_summary', 'N/A')}")
        else:
            st.info("无匹配结果数据")

    with tab3:
        advice = data.get("optimization_advice", "") or ""
        if advice:
            st.markdown(advice)
        else:
            st.info("无优化建议数据")

    st.markdown("---")

# ======================================================================
# UI COMPONENT: Main — Resume Input & Diagnosis
# ======================================================================
def render_main_diagnosis():
    """Render the main diagnosis interface: resume input, matching, optimization."""
    if st.session_state.selected_history_data:
        return  # History playback takes precedence

    st.markdown("""
    <div style="text-align:center;margin-bottom:24px;">
      <h1 style="margin-bottom:0;">🎯 AI 求职智能匹配与简历优化智能体</h1>
      <p style="color:#888;font-size:16px;">上传简历 → AI匹配最佳岗位 → STAR法则深度优化</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.is_logged_in:
        st.info("👈 **请先在侧边栏使用QQ邮箱登录**，然后即可开始智能诊断。")
        st.markdown("---")
        # Show a preview of available jobs
        st.markdown("### 📋 当前可匹配岗位一览")
        jobs = load_jobs_db()
        if jobs:
            cols = st.columns(3)
            for i, job in enumerate(jobs):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{job['title']}**")
                        st.caption(f"🏢 {job['company']} · 📍 {job['location']}")
                        st.caption(f"💰 {job['salary']}")
        return

    # ── Logged in: Show diagnosis interface ────────────────────────────
    st.markdown("### 📝 第一步：粘贴简历内容")
    st.caption("请将你的完整简历内容粘贴到下方文本框（支持Markdown格式）")

    resume_text = st.text_area(
        "简历内容",
        value=st.session_state.resume_input,
        height=280,
        placeholder="""请在此粘贴你的简历内容，建议包含：

- 📚 教育背景（学校、专业、GPA、相关课程）
- 💼 实习/项目经历（公司、岗位、工作内容、成果）
- 🛠️ 技术栈（编程语言、框架、工具、证书）
- 🏆 竞赛/获奖/论文/开源贡献
- 🎯 求职意向（期望岗位方向、城市）

例如：
教育背景：XX大学 计算机科学与技术 本科 2025届 GPA 3.8/4.0
实习经历：XX科技公司 后端开发实习生 2024.06-2024.09
- 参与电商交易系统开发，使用Go语言重构订单模块
- 优化MySQL慢查询，QPS从200提升至800
...
""",
        key="resume_text_input",
    )
    st.session_state.resume_input = resume_text

    # ── Diagnose button ──────────────────────────────────────────────
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
    with col_btn2:
        start_disabled = len(resume_text.strip()) < 50
        if st.button(
            "🚀 开始智能诊断",
            use_container_width=True,
            type="primary",
            disabled=start_disabled,
        ):
            if start_disabled:
                st.warning("简历内容至少需要50个字符，请完善后再提交。")
            else:
                st.session_state.diagnosis_running = True
                st.session_state.matched_jobs = []
                st.session_state.optimization_advice = ""
                st.session_state.selected_job_id = None
                st.session_state.selected_history_id = None
                st.session_state.selected_history_data = None

    if start_disabled and resume_text.strip():
        st.caption(f"当前已输入 {len(resume_text.strip())} 字符，至少需要50字符")

    # ── Step A: Job Matching ─────────────────────────────────────────
    if st.session_state.diagnosis_running and not st.session_state.matched_jobs:
        st.markdown("---")
        st.markdown("### 🎯 第一步：AI岗位智能匹配中...")

        jobs = load_jobs_db()
        llm_client = get_llm_client()

        if not jobs:
            st.error("❌ 岗位数据库为空，请检查 jobs_db.json")
            st.session_state.diagnosis_running = False
            return

        if not llm_client:
            st.error("❌ LLM API 未配置，请在 secrets 中配置 [llm]")
            st.session_state.diagnosis_running = False
            return

        with st.spinner("🤖 AI正在深度分析你的简历，与12个校招岗位进行语义级比对..."):
            matches = llm_job_matching(llm_client, resume_text, jobs)

        if matches:
            st.session_state.matched_jobs = matches
            st.rerun()
        else:
            st.session_state.diagnosis_running = False
            st.error("❌ 岗位匹配失败，请检查API配置或稍后重试")

    # ── Display matching results ─────────────────────────────────────
    if st.session_state.matched_jobs:
        st.markdown("---")
        st.markdown("### 🎯 AI岗位匹配结果")
        st.caption("以下是根据你的简历语义分析出的 Top 3 最匹配校招岗位")

        matches = st.session_state.matched_jobs
        jobs = load_jobs_db()

        # Build a dict for quick lookup
        job_map = {j["id"]: j for j in jobs}

        for idx, match in enumerate(matches):
            score = match.get("match_score", 0)
            if score >= 80:
                emoji = "🟢"
            elif score >= 60:
                emoji = "🟡"
            else:
                emoji = "🔴"

            with st.container(border=True):
                col_match, col_score = st.columns([4, 1])
                with col_match:
                    st.markdown(f"### {emoji} Top {idx+1}: {match.get('job_title', '?')}")
                    st.caption(f"🏢 **{match.get('company', '?')}**")
                with col_score:
                    st.metric("匹配度", f"{score}%")

                st.caption(f"**✅ 匹配理由**: {match.get('match_reason', 'N/A')}")
                st.caption(f"**⚠️ 核心差距**: {match.get('gap_summary', 'N/A')}")

                # Full job detail expander
                job_id = match.get("job_id")
                full_job = job_map.get(job_id)
                if full_job:
                    with st.expander("📋 查看完整JD"):
                        st.markdown(f"**岗位**: {full_job['title']}")
                        st.markdown(f"**部门**: {full_job.get('department', 'N/A')}")
                        st.markdown(f"**薪资**: {full_job.get('salary', 'N/A')}")
                        st.markdown(f"**职责**: {full_job['jd']}")
                        st.markdown(f"**要求**: {full_job['requirements']}")

                # Select button for optimization
                if st.button(f"✨ 选择此岗位进行深度优化", key=f"optimize_{idx}", use_container_width=True):
                    st.session_state.selected_job_id = match.get("job_id")
                    st.rerun()

        # ── Step B: Resume Optimization ────────────────────────────────
        if st.session_state.selected_job_id:
            st.markdown("---")
            st.markdown("### 📝 第二步：AI简历深度优化（STAR法则）")

            selected_job = job_map.get(st.session_state.selected_job_id)

            if selected_job and not st.session_state.optimization_advice:
                llm_client = get_llm_client()
                if llm_client:
                    with st.spinner("🤖 AI正在以首席HR副总裁身份对你的简历进行深度Gap分析，并生成STAR法则修改范例..."):
                        advice = llm_resume_optimization(llm_client, resume_text, selected_job)

                    if advice:
                        st.session_state.optimization_advice = advice

                        # Save to Supabase
                        supabase = get_supabase_client()
                        if supabase:
                            save_diagnosis_history(
                                supabase,
                                st.session_state.user_email,
                                resume_text,
                                matches,
                                advice,
                            )
                            # Refresh history
                            st.session_state.history_records = fetch_user_history(
                                supabase, st.session_state.user_email
                            )
                        st.rerun()

            # Display optimization advice
            if st.session_state.optimization_advice:
                st.markdown(st.session_state.optimization_advice)

                # Action buttons
                col_action1, col_action2, col_action3 = st.columns(3)
                with col_action1:
                    if st.button("🔄 重新诊断", use_container_width=True):
                        st.session_state.matched_jobs = []
                        st.session_state.optimization_advice = ""
                        st.session_state.selected_job_id = None
                        st.session_state.diagnosis_running = True
                        st.rerun()
                with col_action2:
                    if st.button("🔙 返回匹配结果", use_container_width=True):
                        st.session_state.optimization_advice = ""
                        st.session_state.selected_job_id = None
                        st.rerun()
                with col_action3:
                    st.caption("💡 点击上方文本可复制STAR范例")


# ======================================================================
# UI COMPONENT: Footer
# ======================================================================
def render_footer():
    """Render the app footer."""
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align:center;color:#999;font-size:12px;padding:20px 0;">
        🎯 <strong>AI 求职智能匹配与简历优化智能体</strong> · Powered by Streamlit + Supabase + LLM<br>
        ⚠️ AI诊断建议仅供参考，请结合自身实际情况修改简历 · 您的隐私数据通过Supabase加密存储
    </div>
        """,
        unsafe_allow_html=True,
    )


# ======================================================================
# MAIN ENTRY POINT
# ======================================================================
def main():
    """Main application entry point."""
    init_session_state()

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/job.png",
            width=64,
        )
        st.markdown("# 🎯 AI求职智能体")
        st.caption("你的专属求职匹配与简历优化助手")

    render_sidebar_auth()
    render_sidebar_history()

    # ── Main Content ──────────────────────────────────────────────────
    if st.session_state.selected_history_data:
        render_history_playback()
    else:
        render_main_diagnosis()

    render_footer()


if __name__ == "__main__":
    main()
