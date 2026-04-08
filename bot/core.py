"""核心机器人逻辑 - 针对 wxauto4（开源版本）"""
import os
import logging
import time
from typing import Dict, Callable, Any, Optional
from threading import Thread, Event

import openai
import requests
from wxauto4 import WeChat

# Windows COM 初始化（必需）
try:
    import pythoncom
    HAS_PYTHONCOM = True
except ImportError:
    HAS_PYTHONCOM = False

logger = logging.getLogger(__name__)


class AutoReplyBot:
    """微信自动回复机器人 - wxauto4 开源版本"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化机器人
        
        Args:
            config: 配置字典，包含:
                - api_key: OpenAI API key
                - api_base_url: API 基础 URL
                - model: 模型名称
                - system_prompt: 系统提示词
                - listen_friends: 要监听的联系人列表
        """
        self.config = config
        self.wx = None
        self.client = None
        self.running = False
        self.status_callback = None
        self.stop_event = Event()
        
        # 消息去重缓存：{friend_name: set(message_hashes)}
        self.message_cache = {}
        
        # 轮询间隔（秒）
        self.poll_interval = float(os.getenv("POLL_INTERVAL", "2"))
        
        # 当前用户的昵称（稍后初始化）
        self.self_nickname = None
        
        self._init_ai_client()
    
    def _init_ai_client(self):
        """初始化 AI 客户端"""
        api_key = self.config.get('api_key', '')
        api_base_url = self.config.get('api_base_url', '')
        
        if api_key:
            try:
                self.client = openai.OpenAI(
                    api_key=api_key, 
                    base_url=api_base_url or None
                )
            except Exception as e:
                logger.error(f"初始化 OpenAI 客户端失败: {e}")
    
    def _get_ai_response(self, prompt: str) -> str:
        """获取 AI 回复"""
        if not prompt:
            return ""
        
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.config.get('model', 'deepseek-chat'),
                    messages=[
                        {"role": "system", "content": self.config.get('system_prompt', '')},
                        {"role": "user", "content": prompt},
                    ],
                    stream=False,
                    temperature=0.5,
                )
                reply = response.choices[0].message.content
                return reply.strip() if reply else ""
            except Exception as e:
                logger.warning(f"OpenAI SDK 调用失败: {e}")
        
        # 回退到 DeepSeek API
        api_key = self.config.get('api_key', '')
        if not api_key:
            return "【AI配置缺失】"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.config.get('model', 'deepseek-chat'),
            "messages": [
                {"role": "system", "content": self.config.get('system_prompt', '')},
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
            return f"【AI 接口错误】{response.status_code}"
        except Exception as e:
            return f"【AI 大脑断线】{str(e)}"
    
    def _is_message_from_friend(self, msg, friend_name: str) -> bool:
        """判断消息是否来自好友而非自己发送
        
        Args:
            msg: 消息对象
            friend_name: 好友名称
            
        Returns:
            True 表示来自好友，False 表示自己发送的
        """
        try:
            # 首先检查内容
            content = getattr(msg, 'content', '')
            if not content:
                return False
            
            # 过滤掉特殊消息：纯数字、特殊符号等（通常是系统消息或时间戳）
            if content.strip().isdigit() or len(content.strip()) <= 2:
                # 纯数字或超短内容通常不是真实用户消息
                # 但要保留短消息如 "hi", "ok" 等
                if content.strip().isdigit():
                    return False
            
            # 方法1: 检查 sender 字段（最准确）
            sender = getattr(msg, 'sender', '')
            if sender:
                # 如果 sender 就是好友名称，说明是来自好友
                if sender == friend_name:
                    return True
                # 如果 sender 是自己，说明是自己发的
                if self.self_nickname and sender == self.self_nickname:
                    return False
            
            # 方法2: 通过 attr 字段判断
            # 'self' 表示自己发送，其他表示来自对方
            attr = getattr(msg, 'attr', '')
            if attr == 'self':
                return False
            if attr and attr != 'self':
                # 有明确的非self标记，认为是来自好友
                return True
            
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
    
    def _update_status(self, message: str):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)
    
    
    def _process_friend_messages(self, friend_name: str):
        """处理某个好友的消息"""
        try:
            # 切换到聊天窗口
            self.wx.ChatWith(friend_name)
            time.sleep(0.2)  # 等待窗口切换
            
            # 获取所有消息
            msgs = self.wx.GetAllMessage()
            if not msgs:
                return
            
            # 初始化此好友的消息缓存集合（如果不存在）
            if friend_name not in self.message_cache:
                self.message_cache[friend_name] = set()
            
            # 倒序遍历，找最新的入站消息
            for msg in reversed(msgs):
                # 跳过没有 content 的消息
                if not hasattr(msg, 'content') or not msg.content:
                    continue
                
                content = msg.content.strip()
                
                # 跳过空内容
                if not content:
                    continue
                
                # 检查是否是来自好友的消息（使用改进的判断方法）
                if not self._is_message_from_friend(msg, friend_name):
                    continue
                
                # 生成消息唯一标识，结合内容和先发时间
                msg_time = getattr(msg, 'create_time', '')
                msg_id = getattr(msg, 'id', '')
                
                # 使用多个属性生成hash，提高可靠性
                if msg_id:
                    msg_hash = f"{friend_name}:{msg_id}"
                elif msg_time:
                    msg_hash = f"{friend_name}:{content}:{msg_time}"
                else:
                    msg_hash = f"{friend_name}:{content}"
                
                # 检查是否已处理过此消息
                if msg_hash in self.message_cache[friend_name]:
                    continue
                
                # 记录此消息的 hash（添加到集合，而非替换）
                self.message_cache[friend_name].add(msg_hash)
                
                logger.info(f"收到【{friend_name}】: {content}")
                self._update_status(f"收到【{friend_name}】的消息")
                
                # 调用 AI 获取回复
                reply = self._get_ai_response(content)
                if not reply:
                    continue
                
                # 发送回复
                try:
                    self.wx.SendMsg(reply, friend_name)
                    logger.info(f"已回复【{friend_name}】: {reply}")
                    self._update_status(f"已回复【{friend_name}】")
                except Exception as e:
                    logger.error(f"发送消息失败【{friend_name}】: {e}")
                    self._update_status(f"发送失败: {str(e)}")
                
                # 只处理最新的一条消息，然后继续轮询
                break
                
        except Exception as e:
            logger.error(f"处理【{friend_name}】消息失败: {e}")
    
    def start(self, status_callback: Callable[[str], None] = None):
        """启动机器人"""
        self.status_callback = status_callback
        self.stop_event.clear()
        
        # Windows COM 初始化
        if HAS_PYTHONCOM:
            try:
                pythoncom.CoInitialize()
                logger.info("COM 已初始化")
            except Exception as e:
                logger.warning(f"COM 初始化警告: {e}")
        
        try:
            self._update_status("正在初始化 WeChat...")
            self.wx = WeChat()
            
            # 尝试获取当前用户的昵称
            try:
                self.self_nickname = self.wx.nickname
                logger.info(f"当前登录用户: {self.self_nickname}")
            except Exception as e:
                logger.warning(f"无法获取当前用户昵称: {e}")
                # 继续运行，使用其他判断方法
            
            self.running = True
            
            listen_list = self.config.get('listen_friends', [])
            self._update_status(f"准备监听 {len(listen_list)} 个联系人...")
            
            # 初始化消息缓存（使用集合存储所有已处理的消息）
            for friend_name in listen_list:
                self.message_cache[friend_name] = set()
            
            logger.info(f"机器人已启动，轮询间隔: {self.poll_interval}s")
            self._update_status(f"机器人已启动，轮询中...")
            
            # 轮询消息检查
            while self.running and not self.stop_event.is_set():
                try:
                    for friend_name in listen_list:
                        if not self.running:
                            break
                        self._process_friend_messages(friend_name)
                    
                    # 等待下一个轮询周期
                    time.sleep(self.poll_interval)
                    
                except Exception as e:
                    logger.error(f"轮询循环异常: {e}")
                    time.sleep(self.poll_interval)
            
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logger.error(f"启动失败: {e}")
            self._update_status(f"启动失败: {str(e)}")
            self.running = False
        finally:
            # 清理 COM 资源
            if HAS_PYTHONCOM:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
    
    def start_async(self, status_callback: Callable[[str], None] = None):
        """在后台线程启动机器人"""
        thread = Thread(target=self.start, args=(status_callback,), daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """停止机器人"""
        self.running = False
        self.stop_event.set()
        self._update_status("机器人已停止")
        logger.info("机器人已停止")

