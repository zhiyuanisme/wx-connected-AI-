# 微信 AI 自动回复

一个基于 `wxauto4` 的微信自动回复程序，支持接入 OpenAI 兼容接口（如 DeepSeek）。提供**图形界面**和**命令行**两种使用方式。

## 功能

- ✅ **图形界面** - 点击运行，无需编程基础
- ✅ **事件监听** - 实时响应，低 CPU 占用
- ✅ **AI 回复** - 支持 OpenAI 兼容的 API（DeepSeek、GPT 等）
- ✅ 监听多个联系人
- ✅ 自定义系统提示词
- ✅ 自动去重与防重复回复

## 项目结构

```
wechat_auto_reply/
├── app.py          # 📌 GUI 应用入口（推荐）
├── test.py         # 命令行版本
├── bot/
│   ├── core.py     # 核心机器人逻辑
│   └── config.py   # 配置管理
├── gui/
│   └── gui_app.py  # GUI 界面
├── config.json     # 配置文件（自动生成）
└── README.md
```

## 快速开始

### 方式一：GUI 应用（推荐，适合普通用户）

1. **启动应用**
   ```powershell
   # Windows 直接双击 app.py 或在 PowerShell 运行：
   python app.py
   ```

2. **进行配置**
   - 在"配置"标签页填入：
     - **API Key**：你的 DeepSeek/OpenAI API Key
     - **API 地址**：默认为 https://gpt-agent.cc/v1
     - **监听联系人**：微信中的显示名，多个用逗号分隔
     - **系统提示词**：可选，决定 AI 的回复风格

3. **点击启动**
   - 在"控制"标签页点击"启动机器人"
   - 在"日志"标签页查看运行状态

### 方式二：命令行（适合开发者）

1. 复制环境变量
   ```powershell
   Copy-Item .env.example .env
   ```

2. 编辑 `.env`，填入 API Key 和监听联系人

3. 运行
   ```powershell
   python test.py
   ```

## 环境要求

- Windows 系统
- Python 3.11+
- 已安装并登录微信客户端

## 安装依赖

如果是新环境，先激活虚拟环境：

```powershell
.\自动回复\Scripts\Activate.ps1
```

然后安装依赖：

```powershell
pip install wxauto4 openai requests python-dotenv
```

## 配置说明

### 配置文件位置

- **GUI 应用**：配置保存在 `config.json`（自动生成）
- **命令行版本**：配置保存在 `.env`

### 配置项

| 项目 | 说明 | 示例 |
|---|----|-----|
| `api_key` | API 密钥 | `sk-xxxxx` |
| `api_base_url` | API 地址 | `https://gpt-agent.cc/v1` |
| `model` | 模型名称 | `deepseek-chat` |
| `system_prompt` | 系统提示词 | `你是一个易怒的助手` |
| `listen_friends` | 监听联系人 | `文件传输助手,张三` |

## 常见问题

### 1. 启动后没有收到消息回复

- ✅ 检查微信是否已登录
- ✅ 检查联系人名称是否与微信显示名完全一致
- ✅ 在"日志"标签页查看错误信息

### 2. API Key 显示无效

- 确保 API Key 格式正确
- 检查网络连接
- 测试 API 是否可用

### 3. 提示"【AI配置缺失】"

- 确保填入了 API Key
- 保存配置后再启动

## 打包成 EXE（可选）

想让别人不用装 Python 也能运行？可以打包成 .exe：

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --name WeChat-Auto-Reply app.py
```

生成的 exe 在 `dist` 文件夹中。

## 文件说明

| 文件 | 用途 |
|-----|------|
| [app.py](app.py) | GUI 应用入口 |
| [test.py](test.py) | 命令行版本 |
| [bot/core.py](bot/core.py) | 核心机器人逻辑 |
| [bot/config.py](bot/config.py) | 配置管理 |
| [gui/gui_app.py](gui/gui_app.py) | GUI 界面代码 |

## 注意事项

⚠️ **重要提示**

- 不建议频繁自动回复，可能被 WeChat 判定为营销
- API Key 请妥善保管，不要分享给他人
- `.env` 和 `config.json` 包含敏感信息，不要提交到公开仓库
- 自动回复行为请遵守 WeChat 服务条款和法律法规

## 更新日志

### v2.0（GUI 版本）
- ✨ 新增图形界面应用
- 🚀 改为事件监听模式（比轮询快 10 倍）
- 📝 支持配置文件持久化
- 🎯 大幅简化使用流程

### v1.0（命令行版本）
- 基础命令行版本

## 支持与反馈

- 📧 如有问题，请检查"日志"标签页的错误信息
- 🐛 发现 Bug？欢迎提交 Issue

## 许可证

MIT License

