# 微信 AI 自动回复

一个基于 `wxauto4` 的微信自动回复脚本，支持接入 OpenAI 兼容接口（如 DeepSeek）。

## 功能

- 监听指定微信联系人消息
- 使用 AI 生成回复内容
- 自动发送回复
- 基础防重复回复策略（消息去重、短时重复文本抑制）

## 项目结构

```text
wechat_auto_reply/
  test.py               # 主程序
  .env.example          # 环境变量示例
  .gitignore
  README.md
```

## 运行环境

- Windows
- 已安装并登录微信客户端
- Python 3.11（建议）

## 安装依赖

如果你使用本项目已有虚拟环境，可先激活：

```powershell
.\自动回复\Scripts\Activate.ps1
```

如果你是新环境，先安装依赖：

```powershell
pip install wxauto4 openai requests python-dotenv
```

## 配置

1. 复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

2. 编辑 `.env`，至少填写：

```env
OPENAI_API_KEY=你的API_KEY
OPENAI_BASE_URL=https://gpt-agent.cc/v1
OPENAI_MODEL=deepseek-chat
LISTEN_FRIENDS=文件传输助手,王辉
```

可选项：

- `SYSTEM_PROMPT`：系统提示词
- `POLL_INTERVAL`：轮询间隔（秒）
- `DEEPSEEK_API_URL`：回退请求地址
- `DEEPSEEK_API_KEY`：当 `OPENAI_API_KEY` 为空时使用

## 启动

```powershell
python .\test.py
```

启动后控制台会输出监听对象，按 `Ctrl + C` 可停止。

## 注意事项

- 首次运行前请确认微信已登录且聊天窗口可访问。
- 不建议将 `.env` 提交到仓库（已在 `.gitignore` 中忽略）。
- 自动回复行为请遵守平台规则与法律法规。

## 常见问题

### 1. 提示 AI 配置缺失

请检查 `.env` 是否存在并包含 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`。

### 2. 没有自动回复

- 检查 `LISTEN_FRIENDS` 名称是否和微信联系人显示名完全一致
- 检查网络是否正常
- 查看终端日志和 `wxauto_logs` 输出

### 3. 提交 Git 报身份错误

执行以下命令配置 Git 身份：

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```
