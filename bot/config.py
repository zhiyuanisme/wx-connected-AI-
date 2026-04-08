"""配置管理模块"""
import os
import json
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(__file__).parent.parent / "config.json"
ENV_FILE = Path(__file__).parent.parent / ".env"


class Config:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        "api_key": "",
        "api_base_url": "https://gpt-agent.cc/v1",
        "model": "deepseek-chat",
        "system_prompt": "你是一个易怒的微信助手，请简短回答。",
        "listen_friends": ["文件传输助手"],
        "enabled": False,
    }
    
    @staticmethod
    def load() -> Dict[str, Any]:
        """从 config.json 加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return Config.DEFAULT_CONFIG.copy()
    
    @staticmethod
    def save(config: Dict[str, Any]) -> bool:
        """保存配置到 config.json"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    @staticmethod
    def export_to_env(config: Dict[str, Any]) -> bool:
        """导出配置到 .env 文件"""
        try:
            lines = [
                f"OPENAI_API_KEY={config.get('api_key', '')}",
                f"OPENAI_BASE_URL={config.get('api_base_url', '')}",
                f"OPENAI_MODEL={config.get('model', 'deepseek-chat')}",
                f"SYSTEM_PROMPT={config.get('system_prompt', '')}",
                f"LISTEN_FRIENDS={','.join(config.get('listen_friends', []))}",
            ]
            with open(ENV_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True
        except Exception as e:
            print(f"导出 .env 失败: {e}")
            return False
