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
from wxauto4.msgs import FriendMessage, FriendTextMessage

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
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")

client = None
if OPENAI_API_KEY:
    client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)


def get_ai_response(prompt: str) -> str:
    """优先用 openai SDK，失败后回退到 requests 直连 DeepSeek API。"""
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
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=20)
        if response.status_code == 200:
            response_data = response.json()
            reply = response_data["choices"][0]["message"].get("content", "")
            return reply.strip() if reply else ""
        return f"【AI接口失败】状态码: {response.status_code}"
    except Exception as e:
        return f"【AI大脑断线】: {e}"


def on_message(msg, chat) -> None:
    """消息回调函数 - 当监听的联系人发送消息时自动触发"""
    if not isinstance(msg, FriendMessage):
        return
    
    if not isinstance(msg, FriendTextMessage):
        logger.info(f"收到【{chat.who}】的非文本消息，类型: {msg.type}")
        return
    
    content = msg.content.strip()
    if not content:
        return
    
    logger.info(f"收到【{chat.who}】: {content}")
    
    reply = get_ai_response(content)
    if not reply:
        return
    
    try:
        chat.SendMsg(reply)
        logger.info(f"已回复【{chat.who}】: {reply}")
    except Exception as e:
        logger.error(f"发送失败【{chat.who}】: {e}")


def main() -> None:
    """主程序 - 使用事件监听模式"""
    wx = WeChat()
    
    listen_list = [
        name.strip() 
        for name in os.getenv("LISTEN_FRIENDS", "文件传输助手").split(",") 
        if name.strip()
    ]
    
    logger.info(f"准备监听 {len(listen_list)} 个联系人")
    
    for friend_name in listen_list:
        try:
            wx.AddListenChat(nickname=friend_name, callback=on_message)
            logger.info(f"已添加监听【{friend_name}】")
        except Exception as e:
            logger.error(f"添加监听失败【{friend_name}】: {e}")
    
    logger.info("机器人已启动，监听中...")
    
    try:
        # 尝试使用 KeepRunning，如果不可用则使用轮询
        try:
            wx.KeepRunning()
        except (AttributeError, Exception) as keep_error:
            logger.warning(f"KeepRunning 不可用，使用轮询模式: {keep_error}")
            while True:
                time.sleep(1)  # 保持进程运行
    except KeyboardInterrupt:
        logger.info("机器人已停止")


if __name__ == "__main__":
    main()
