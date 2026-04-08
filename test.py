import os
import time

import openai
import requests
from dotenv import load_dotenv
from wxauto4 import WeChat  # 免费版

# 加载环境变量
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "你是一个易怒的微信助手，请简短回答。")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))
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
            print(f"openai SDK 调用失败，准备回退 requests: {e}")

    api_key = OPENAI_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return "【AI配置缺失】请在 .env 配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY"

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
        return f"【AI接口请求失败】状态码: {response.status_code}"
    except Exception as e:
        return f"【AI大脑暂时断线】: {e}"


def is_incoming_message(sender: str, my_name: str, direction: str, attr: str) -> bool:
    """尽量稳健地判断是否是对方发来的入站消息。"""
    if sender:
        return sender != my_name

    text = f"{direction} {attr}".lower()
    if "right" in text or "out" in text or "send" in text or "self" in text or "me" in text:
        return False
    if "left" in text or "in" in text or "recv" in text:
        return True
    return False


def build_msg_key(msg_type: str, content: str, sender: str, direction: str, msg_hash: str | None) -> str:
    """组合去重键，降低重复回复概率。"""
    return str(msg_hash) if msg_hash else f"{sender}:{direction}:{msg_type}:{content}"


def remember_message(key_store: dict[str, list[str]], who: str, msg_key: str, limit: int = 20) -> None:
    """记录最近发送/处理过的消息键。"""
    bucket = key_store.setdefault(who, [])
    bucket.append(msg_key)
    if len(bucket) > limit:
        del bucket[:-limit]


def normalize_text(text: str) -> str:
    """归一化文本，减少空格和换行带来的误判。"""
    return "".join((text or "").split())


def get_message_info(msg):
    """提取消息关键信息。"""
    return {
        "type": getattr(msg, "type", ""),
        "content": getattr(msg, "content", ""),
        "sender": getattr(msg, "sender", ""),
        "direction": getattr(msg, "direction", ""),
        "attr": getattr(msg, "attr", ""),
        "hash": getattr(msg, "hash", None),
    }


def find_latest_incoming_message(msgs, my_name: str):
    """从消息列表末尾向前查找最新的一条对方消息。"""
    for msg in reversed(msgs or []):
        info = get_message_info(msg)
        if info["content"] and is_incoming_message(info["sender"], my_name, str(info["direction"]), str(info["attr"])):
            return info
    return None


def auto_reply_multiple() -> None:
    wx = WeChat()
    my_name = getattr(wx, "nickname", "")
    if not my_name:
        try:
            my_info = wx.GetMyInfo() or {}
            my_name = my_info.get("display_name", "") or my_info.get("nickName", "") or my_info.get("nickname", "")
        except Exception:
            my_name = ""
    listen_list = [name.strip() for name in os.getenv("LISTEN_FRIENDS", "文件传输助手,王辉").split(",") if name.strip()]
    last_seen_message = {name: "" for name in listen_list}
    sent_message_keys = {name: [] for name in listen_list}
    last_sent_text = {name: "" for name in listen_list}
    last_sent_time = {name: 0.0 for name in listen_list}

    # 启动时只记录当前会话的最后一条消息，避免历史消息被自动回复。
    for who in listen_list:
        try:
            wx.ChatWith(who)
            msgs = wx.GetAllMessage() or []
            latest_incoming = find_latest_incoming_message(msgs, my_name)
            if latest_incoming:
                last_seen_message[who] = build_msg_key(
                    latest_incoming["type"],
                    latest_incoming["content"],
                    latest_incoming["sender"],
                    latest_incoming["direction"],
                    latest_incoming["hash"],
                )
        except Exception as e:
            print(f"初始化会话失败【{who}】: {e}")

    print("自动回复机器人已启动，按 Ctrl+C 退出。")
    print(f"监听对象: {listen_list}")

    while True:
        try:
            for who in listen_list:
                wx.ChatWith(who)
                msgs = wx.GetAllMessage() or []

                if not msgs:
                    continue

                latest_incoming = find_latest_incoming_message(msgs, my_name)
                if not latest_incoming:
                    continue

                msg_key = build_msg_key(
                    latest_incoming["type"],
                    latest_incoming["content"],
                    latest_incoming["sender"],
                    latest_incoming["direction"],
                    latest_incoming["hash"],
                )

                if msg_key == last_seen_message[who]:
                    continue

                if msg_key in sent_message_keys[who]:
                    last_seen_message[who] = msg_key
                    continue

                current_text = normalize_text(latest_incoming["content"])
                if current_text and current_text == last_sent_text[who] and time.time() - last_sent_time[who] < 10:
                    last_seen_message[who] = msg_key
                    continue

                last_seen_message[who] = msg_key

                content = latest_incoming["content"]
                print(f"最新消息【{who}】 content={content}")

                reply = get_ai_response(content)
                if not reply:
                    continue

                wx.SendMsg(reply, who)
                last_sent_text[who] = normalize_text(reply)
                last_sent_time[who] = time.time()
                remember_message(sent_message_keys, who, build_msg_key("", reply, my_name, "out", None))
                print(f"已回复【{who}】: {reply}")

            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("机器人已停止运行。")
            break
        except Exception as e:
            print(f"监听发生错误: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    auto_reply_multiple()