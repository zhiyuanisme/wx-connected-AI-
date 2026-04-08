"""WeChat AI 自动回复机器人 - GUI 版本入口

直接运行此文件即可启动图形界面应用
"""
import sys
from pathlib import Path

# 确保可以导入 gui 模块
sys.path.insert(0, str(Path(__file__).parent))

from gui.gui_app import main

if __name__ == "__main__":
    main()

