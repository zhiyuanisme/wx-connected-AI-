# 更新日志

## [最新] 轮询模式架构重构

### 背景
前一个版本尝试使用 `wxautox4 Plus` 付费版本的事件监听 API（`AddListenChat()` 和 `KeepRunning()`），但项目使用的是 `wxauto4` 开源免费版本，这些 API 不存在，导致机器人无法监听和回复消息。

### 改动内容

#### ✅ bot/core.py - 核心逻辑重写
- **删除** 依赖 Plus 版本的方法调用
- **新增** `_process_friend_messages()` 轮询处理方法
  - 通过 `ChatWith(friend_name)` 切换到聊天窗口
  - 通过 `GetAllMessage()` 获取所有消息
  - 实现消息去重机制（内置缓存）
  - 识别入站消息（排除自己发送的消息）
  - 生成 AI 回复并通过 `SendMsg()` 发送
- **改进** `start()` 方法
  - 使用 `while self.running` 主轮询循环
  - 可配置轮询间隔 `POLL_INTERVAL` (默认2秒)
  - 正确的 COM 初始化和清理
  - 使用 `threading.Event` 实现优雅停止

#### ✅ test.py - CLI 版本适配
- 改为轮询模式
- 移除对 `FriendMessage` 和 `FriendTextMessage` 的依赖
- 相同的消息处理逻辑

#### ✅ gui/gui_app.py - GUI 应用
- 无需改动（接口保持一致）
- 现在能正常工作

#### ✅ README.md - 文档更新
- 更新功能说明
- 新增轮询间隔配置说明
- 更新常见问题

### 技术细节

#### 消息去重机制
```python
message_cache = {friend_name: last_message_hash}
```
- 使用消息内容 hash 作为唯一标识
- 防止同一条消息被重复处理

#### 发件人识别
```python
is_self = (attr == 'self' or sender == '我' or direction == 'right')
```
- 通过多个属性判断确保准确识别来源
- 排除机器人自己发送的消息

#### 轮询流程
```
遍历联系人 → ChatWith() → GetAllMessage() → 去重 → 识别入站 → AI回复 → SendMsg()
```
- 每个周期 POLL_INTERVAL 秒
- 每个联系人每次仅处理最新的一条新消息

### 兼容性
- ✅ wxauto4 开源版本（免费）
- ✅ Windows 系统
- ✅ Python 3.11+
- ❌ wxautox4 Plus（已废弃）

### 性能
- CPU 占用: 极低（仅 sleep）
- 响应延迟: POLL_INTERVAL 秒
- 建议: POLL_INTERVAL = 2-5 秒

### 测试方式
1. 通过 GUI: `python app.py` → 填配置 → 点启动
2. 通过 CLI: `python test.py` (需要 .env 配置)

### 下次优化方向
- [ ] 支持群聊消息
- [ ] 支持语音消息回复
- [ ] 更精细的消息过滤
- [ ] 打包成独立 .exe
