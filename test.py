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
self_nickname = None


def is_message_from_friend(msg, friend_name: str) -> bool:
    """判断消息是否来自好友而非自己发送
    
    Args:
        msg: 消息对象
        friend_name: 好友名称
        
    Returns:
        True 表示来自好友，False 表示自己发送的
    """
    global self_nickname
    
    try:
        # 方法1: 检查 sender 字段
        sender = getattr(msg, 'sender', '')
        
        # 如果 sender 就是好友名称，说明是来自好友
        # 如果 sender 是自己，说明是自己发的
        if sender:
            if sender == friend_name:
                return True
            if self_nickname and sender == self_nickname:
                return False
        
        # 方法2: 通过 attr 字段判断
        # 'self' 表示自己发送，其他表示来自对方
        attr = getattr(msg, 'attr', '')
        if attr == 'self':
            return False
        
        # 方法3: 通过 direction 字段判断
        # 'right' 表示右对齐（自己），'left' 表示左对齐（对方）
        direction = getattr(msg, 'direction', '')
        if direction == 'right':
            return False
        elif direction == 'left':
            return True
        
        # 默认认为是来自好友
        return True
        
    except Exception as e:
        logger.warning(f"判断消息来源时出错: {e}")
        return False


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
            
            # 检查是否是来自好友的消息（使用改进的判断方法）
            if not is_message_from_friend(msg, friend_name):
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
    global self_nickname
    
    wx = WeChat()
    
    # 尝试获取当前用户的昵称
    try:
        self_nickname = wx.nickname
        logger.info(f"当前登录用户: {self_nickname}")
    except Exception as e:
        logger.warning(f"无法获取当前用户昵称: {e}")
        # 继续运行，使用其他判断方法
    
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

