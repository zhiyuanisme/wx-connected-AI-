"""核心机器人逻辑"""
import os
import logging
import time
from typing import Dict, Callable, Any
from threading import Thread

import openai
import requests
from wxauto4 import WeChat
from wxauto4.msgs import FriendMessage, FriendTextMessage

logger = logging.getLogger(__name__)


class AutoReplyBot:
    """微信自动回复机器人"""
    
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
    
    def _on_message(self, msg, chat):
        """消息回调函数"""
        if not isinstance(msg, FriendMessage):
            return
        
        if not isinstance(msg, FriendTextMessage):
            logger.info(f"收到【{chat.who}】的非文本消息")
            return
        
        content = msg.content.strip()
        if not content:
            return
        
        logger.info(f"收到【{chat.who}】: {content}")
        self._update_status(f"收到【{chat.who}】的消息")
        
        reply = self._get_ai_response(content)
        if not reply:
            return
        
        try:
            chat.SendMsg(reply)
            logger.info(f"已回复【{chat.who}】: {reply}")
            self._update_status(f"已回复【{chat.who}】")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            self._update_status(f"发送失败: {str(e)}")
    
    def _update_status(self, message: str):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)
    
    def start(self, status_callback: Callable[[str], None] = None):
        """启动机器人"""
        self.status_callback = status_callback
        
        try:
            self._update_status("正在初始化 WeChat...")
            self.wx = WeChat()
            self.running = True
            
            listen_list = self.config.get('listen_friends', [])
            self._update_status(f"准备监听 {len(listen_list)} 个联系人...")
            
            for friend_name in listen_list:
                try:
                    self.wx.AddListenChat(nickname=friend_name, callback=self._on_message)
                    self._update_status(f"已添加监听: {friend_name}")
                    logger.info(f"已添加监听【{friend_name}】")
                except Exception as e:
                    logger.error(f"添加监听失败【{friend_name}】: {e}")
                    self._update_status(f"添加监听失败: {friend_name}")
            
            self._update_status("机器人已启动，等待消息...")
            logger.info("机器人已启动，监听中...")
            
            # 使用 KeepRunning() 或持续轮询来保持程序运行
            try:
                self.wx.KeepRunning()
            except (AttributeError, Exception) as e:
                # 如果 KeepRunning 不可用或出错，使用持续轮询
                logger.warning(f"KeepRunning 不可用，使用轮询模式: {e}")
                while self.running:
                    try:
                        time.sleep(1)  # 每秒检查一次
                    except KeyboardInterrupt:
                        break
            
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            logger.error(f"启动失败: {e}")
            self._update_status(f"启动失败: {str(e)}")
            self.running = False
    
    def start_async(self, status_callback: Callable[[str], None] = None):
        """在后台线程启动机器人"""
        thread = Thread(target=self.start, args=(status_callback,), daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """停止机器人"""
        self.running = False
        self._update_status("机器人已停止")
        logger.info("机器人已停止")
