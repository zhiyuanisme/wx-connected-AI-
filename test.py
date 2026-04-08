import os
import logging
import time

# Windows COM 初始化（必需）
try:
    import pythoncom
    pythoncom.CoInitialize()
except ImportError:
    pass

import openai
import requests
from dotenv import load_dotenv
from wxauto4 import WeChat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "你是一个易怒的微信助手，请简短回答。")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))

client = None
if OPENAI_API_KEY:
    client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)

# 消息去重缓存
message_cache = {}


def get_ai_response(prompt: str) -> str:
    """获取 AI 回复"""
    if not prompt:
        return ""

    if client is not None:
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                temperature=0.5,
            )
            reply = response.choices[0].message.content
            if reply:
                return reply.strip()
        except Exception as e:
            logger.warning(f"openai SDK 调用失败: {e}")

    api_key = OPENAI_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return "【AI配置缺失】请在 .env 配置 OPENAI_API_KEY"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=20
        )
        if response.status_code == 200:
            response_data = response.json()
            reply = response_data["choices"][0]["message"].get("content", "")
            return reply.strip() if reply else ""
        return f"【AI接口失败】状态码: {response.status_code}"
    except Exception as e:
        return f"【AI大脑断线】: {e}"


def process_friend_messages(wx: WeChat, friend_name: str) -> None:
    """处理某个好友的消息"""
    try:
        # 切换到聊天窗口
        wx.ChatWith(friend_name)
        time.sleep(0.2)  # 等待窗口切换
        
        # 获取所有消息
        msgs = wx.GetAllMessage()
        if not msgs:
            return
        
        # 倒序遍历，找最新的入站消息
        for msg in reversed(msgs):
            # 跳过没有 content 的消息
            if not hasattr(msg, 'content') or not msg.content:
                continue
            
            # 检查是否是自己的消息
            sender = getattr(msg, 'sender', '')
            attr = getattr(msg, 'attr', '')
            direction = getattr(msg, 'direction', '')
            
            # 判断是否是来自好友的消息（不是自己发送的）
            is_self = (attr == 'self' or sender == '我' or direction == 'right')
            if is_self:
                continue
            
            # 获取消息 hash 用于去重
            msg_hash = getattr(msg, 'hash', None)
            if not msg_hash:
                msg_hash = f"{friend_name}:{msg.content}"
            
            # 检查是否已处理过此消息
            if msg_hash == message_cache.get(friend_name):
                continue
            
            # 记录此消息的 hash
            message_cache[friend_name] = msg_hash
            
            content = msg.content.strip()
            logger.info(f"收到【{friend_name}】: {content}")
            
            # 调用 AI 获取回复
            reply = get_ai_response(content)
            if not reply:
                continue
            
            # 发送回复
            try:
                wx.SendMsg(reply, friend_name)
                logger.info(f"已回复【{friend_name}】: {reply}")
            except Exception as e:
                logger.error(f"发送消息失败【{friend_name}】: {e}")
            
            # 只处理最新的一条消息，然后继续轮询
            break
                
    except Exception as e:
        logger.error(f"处理【{friend_name}】消息失败: {e}")


def main() -> None:
    """主程序 - 使用轮询模式兼容 wxauto4 开源版本"""
    wx = WeChat()
    
    listen_list = [
        name.strip() 
        for name in os.getenv("LISTEN_FRIENDS", "文件传输助手").split(",") 
        if name.strip()
    ]
    
    logger.info(f"准备监听 {len(listen_list)} 个联系人")
    logger.info(f"轮询间隔: {POLL_INTERVAL}s")
    
    # 初始化消息缓存
    for friend_name in listen_list:
        message_cache[friend_name] = None
    
    logger.info("机器人已启动，轮询中...")
    
    try:
        # 轮询消息检查
        while True:
            try:
                for friend_name in listen_list:
                    process_friend_messages(wx, friend_name)
                
                # 等待下一个轮询周期
                time.sleep(POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"轮询循环异常: {e}")
                time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("机器人已停止")


if __name__ == "__main__":
    main()

