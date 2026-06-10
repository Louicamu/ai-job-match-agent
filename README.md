---
title: AI Job Match & Resume Optimizer
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: streamlit
sdk_version: "1.42.0"
app_file: app.py
pinned: false
python_version: "3.11"
---

# 🎯 AI 求职智能匹配与简历优化智能体

基于大语言模型的智能求职助手 — 一键匹配最佳岗位，STAR法则深度优化简历。

## ✨ 功能亮点

- **🔐 QQ邮箱无密登录** — 6位验证码一键登录/注册，无需记忆密码
- **🤖 AI岗位智能匹配** — 将你的简历与12个校招热门岗位进行语义级比对，输出Top 3匹配与百分比评分
- **📝 STAR法则简历优化** — AI化身首席大厂HR，用STAR法则（情境·任务·行动·结果）为你量身定制简历修改方案
- **📊 历史记录回放** — 通过Supabase云端持久化，随时回顾过往诊断记录
- **🔒 隐私优先** — 本地不落盘任何用户隐私数据，所有信息加密传输至Supabase

## 🚀 本地运行

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd <repo-name>

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置密钥
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
[qq_mail]
sender = "your-email@qq.com"
auth_code = "your-qq-smtp-auth-code"

[supabase]
url = "https://xxxxxxxxxxxx.supabase.co"
anon_key = "eyJhbGciOiJIUzI1NiIs..."

[llm]
api_key = "sk-your-api-key"
base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"
EOF

# 4. 启动应用
streamlit run app.py
```

## 🛠️ 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 & 后端 | Streamlit (Python全栈) |
| 数据库 | Supabase (PostgreSQL) |
| AI引擎 | OpenAI兼容API (DeepSeek/硅基流动/OpenAI) |
| 邮件服务 | QQ邮箱 SMTP (SSL 465) |
| 部署 | Hugging Face Spaces |

## 📁 项目结构

```
.
├── app.py                 # 应用主程序
├── jobs_db.json           # 校招岗位Mock数据库（12个岗位）
├── requirements.txt       # Python依赖清单
├── README.md              # 项目说明（含HF部署元数据）
└── .gitignore             # Git忽略规则
```

## 🔧 Supabase 建表SQL

在Supabase SQL Editor中执行以下语句创建所需表：

```sql
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 历史记录表
CREATE TABLE IF NOT EXISTS history (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
    resume_text TEXT NOT NULL,
    matched_jobs JSONB,
    optimization_advice TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_history_user_email ON history(user_email);
CREATE INDEX idx_history_created_at ON history(created_at DESC);
```

## 📤 部署到 Hugging Face Spaces

```bash
# 1. 在 Hugging Face 创建新 Space（选择 Streamlit SDK）

# 2. 克隆Space仓库
git clone https://huggingface.co/spaces/<your-username>/<your-space-name>
cd <your-space-name>

# 3. 复制项目文件
cp /path/to/project/*.py .
cp /path/to/project/*.json .
cp /path/to/project/requirements.txt .
cp /path/to/project/README.md .
cp /path/to/project/.gitignore .

# 4. 在Space Settings中配置Secrets（Settings > Repository Secrets）
# 添加以下Secret（HF使用双下划线__映射TOML层级）：
#   QQ_MAIL__SENDER
#   QQ_MAIL__AUTH_CODE
#   SUPABASE__URL
#   SUPABASE__ANON_KEY
#   LLM__API_KEY
#   LLM__BASE_URL
#   LLM__MODEL_NAME

# 5. 提交并推送
git add .
git commit -m "Deploy AI Job Match Agent"
git push origin main
```

> **注意**: Hugging Face Spaces的双下划线`__`会自动映射为TOML的嵌套层级。例如设置Secret `QQ_MAIL__SENDER` 等价于 `st.secrets["qq_mail"]["sender"]`。

## ⚠️ 注意事项

1. QQ邮箱SMTP需要使用**授权码**而非QQ密码，在QQ邮箱设置 → 账户 → POP3/SMTP服务中获取
2. LLM API支持所有OpenAI兼容接口（DeepSeek、硅基流动、OpenAI、通义千问等）
3. 首次使用前需在Supabase执行上述建表SQL
4. 验证码有效期为5分钟，每日有发送频率限制

## 📄 License

MIT License — 仅供学习交流使用

---
🤖 Built with [Claude Code](https://claude.com/claude-code)
