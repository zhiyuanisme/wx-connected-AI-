"""打包脚本 - 将 GUI 应用打包成 Windows .exe
使用方法：python build.py
"""
import os
import shutil
import subprocess
import sys

def build():
    """构建 .exe 文件"""
    
    # 检查 PyInstaller 是否安装
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    print("开始打包...")
    
    # 打包命令
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",                          # 生成单个 exe
        "--noconsole",                        # 不显示控制台窗口
        "--name", "WeChat-Auto-Reply",        # 输出文件名
        "--icon", "icon.ico" if os.path.exists("icon.ico") else None,
        "--add-data", "bot:bot",              # 包含 bot 模块
        "--add-data", "gui:gui",              # 包含 gui 模块
        "--collect-all", "wxauto4",           # 收集 wxauto4 所有数据
        "app.py"
    ]
    
    # 移除 None 值
    cmd = [c for c in cmd if c is not None]
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ 打包成功！")
        print("📦 exe 文件位置: dist/WeChat-Auto-Reply.exe")
        print("💡 现在可以将此 exe 文件分享给其他用户")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False
    
    # 清理临时文件
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("WeChat-Auto-Reply.spec"):
        os.remove("WeChat-Auto-Reply.spec")
    
    return True


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
