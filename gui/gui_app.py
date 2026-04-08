"""WeChat AI 自动回复机器人 - GUI 版本"""
import logging
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import sys

# Windows COM 初始化
try:
    import pythoncom
    pythoncom.CoInitialize()
except ImportError:
    pass

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import Config
from bot.core import AutoReplyBot

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GUIApp(tk.Tk):
    """主应用窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.title("WeChat AI 自动回复机器人")
        self.geometry("800x600")
        self.resizable(True, True)
        
        # 初始化变量
        self.config = Config.load()
        self.bot = None
        self.bot_thread = None
        
        # 创建 UI
        self._create_widgets()
        self._load_config_to_ui()
        
        # 关闭窗口时保存配置
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _create_widgets(self):
        """创建 UI 组件"""
        
        # 菜单栏
        menubar = tk.Menu(self)
        self.config_obj = menubar
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="保存配置", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        
        self.config_obj = menubar
        
        # 主容器（使用 Notebook 标签页）
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 配置页
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="配置")
        self._create_config_tab(config_frame)
        
        # 日志页
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="日志")
        self._create_log_tab(log_frame)
        
        # 控制页
        control_frame = ttk.Frame(notebook)
        notebook.add(control_frame, text="控制")
        self._create_control_tab(control_frame)
    
    def _create_config_tab(self, parent):
        """配置标签页"""
        
        # API 配置区
        api_frame = ttk.LabelFrame(parent, text="AI API 配置", padding=10)
        api_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W)
        self.entry_api_key = ttk.Entry(api_frame, show="*", width=60)
        self.entry_api_key.grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        ttk.Label(api_frame, text="API 地址:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_api_url = ttk.Entry(api_frame, width=60)
        self.entry_api_url.grid(row=1, column=1, sticky=tk.EW, padx=5)
        
        ttk.Label(api_frame, text="模型:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.entry_model = ttk.Entry(api_frame, width=60)
        self.entry_model.grid(row=2, column=1, sticky=tk.EW, padx=5)
        
        api_frame.columnconfigure(1, weight=1)
        
        # 监听配置区
        listen_frame = ttk.LabelFrame(parent, text="监听设置", padding=10)
        listen_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(listen_frame, text="监听联系人（用逗号分隔）:").pack(anchor=tk.W)
        self.entry_friends = ttk.Entry(listen_frame, width=80)
        self.entry_friends.pack(fill=tk.X, padx=5, pady=5)
        
        # 提示词配置区
        prompt_frame = ttk.LabelFrame(parent, text="系统提示词", padding=10)
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_prompt = scrolledtext.ScrolledText(prompt_frame, height=6, width=80)
        self.text_prompt.pack(fill=tk.BOTH, expand=True)
        
        # 按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置为默认", command=self.reset_config).pack(side=tk.LEFT, padx=5)
    
    def _create_log_tab(self, parent):
        """日志标签页"""
        
        self.log_display = scrolledtext.ScrolledText(
            parent, 
            state=tk.DISABLED,
            height=20,
            width=100
        )
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建日志处理器
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                self.text_widget.config(state=tk.NORMAL)
                msg = self.format(record) + '\n'
                self.text_widget.insert(tk.END, msg)
                self.text_widget.see(tk.END)
                self.text_widget.config(state=tk.DISABLED)
        
        handler = TextHandler(self.log_display)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        
        # 清空日志按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(button_frame, text="清空日志", command=self._clear_log).pack(side=tk.LEFT)
    
    def _clear_log(self):
        """清空日志"""
        self.log_display.config(state=tk.NORMAL)
        self.log_display.delete(1.0, tk.END)
        self.log_display.config(state=tk.DISABLED)
    
    def _create_control_tab(self, parent):
        """控制标签页"""
        
        # 状态显示
        status_frame = ttk.LabelFrame(parent, text="机器人状态", padding=20)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.label_status = ttk.Label(
            status_frame,
            text="未启动",
            font=("Arial", 20, "bold"),
            foreground="gray"
        )
        self.label_status.pack(pady=20)
        
        # 控制按钮
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        self.btn_start = ttk.Button(
            button_frame,
            text="启动机器人",
            command=self.start_bot,
            width=20
        )
        self.btn_start.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop = ttk.Button(
            button_frame,
            text="停止机器人",
            command=self.stop_bot,
            width=20,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        
        # 提示信息
        info_text = """
使用说明：
1. 在"配置"标签页填入 API Key 和监听联系人
2. 点击"启动机器人"按钮
3. 在"日志"标签页查看运行日志

注意：
- 请确保微信客户端已登录
- API Key 会保存到本地 config.json
- 监听联系人名称需要与微信中的显示名完全一致
        """
        
        info_label = ttk.Label(status_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def _load_config_to_ui(self):
        """从配置加载到 UI"""
        self.entry_api_key.insert(0, self.config.get('api_key', ''))
        self.entry_api_url.insert(0, self.config.get('api_base_url', 'https://gpt-agent.cc/v1'))
        self.entry_model.insert(0, self.config.get('model', 'deepseek-chat'))
        self.entry_friends.insert(0, ','.join(self.config.get('listen_friends', [])))
        self.text_prompt.insert(tk.END, self.config.get('system_prompt', ''))
    
    def _update_config_from_ui(self):
        """从 UI 更新配置"""
        self.config['api_key'] = self.entry_api_key.get()
        self.config['api_base_url'] = self.entry_api_url.get()
        self.config['model'] = self.entry_model.get()
        friends_str = self.entry_friends.get()
        self.config['listen_friends'] = [f.strip() for f in friends_str.split(',') if f.strip()]
        self.config['system_prompt'] = self.text_prompt.get(1.0, tk.END).strip()
    
    def save_config(self):
        """保存配置"""
        self._update_config_from_ui()
        
        if not self.config.get('api_key'):
            messagebox.showwarning("警告", "请填入 API Key")
            return
        
        if not self.config.get('listen_friends'):
            messagebox.showwarning("警告", "请填入监听的联系人")
            return
        
        if Config.save(self.config) and Config.export_to_env(self.config):
            messagebox.showinfo("成功", "配置已保存")
            logger.info("配置已保存")
        else:
            messagebox.showerror("错误", "配置保存失败")
    
    def reset_config(self):
        """重置为默认配置"""
        if messagebox.askyesno("确认", "确认重置为默认配置？"):
            self.config = Config.DEFAULT_CONFIG.copy()
            # 清空 UI
            self.entry_api_key.delete(0, tk.END)
            self.entry_api_url.delete(0, tk.END)
            self.entry_model.delete(0, tk.END)
            self.entry_friends.delete(0, tk.END)
            self.text_prompt.delete(1.0, tk.END)
            # 重新加载
            self._load_config_to_ui()
    
    def start_bot(self):
        """启动机器人"""
        self._update_config_from_ui()
        
        if not self.config.get('api_key'):
            messagebox.showwarning("警告", "请填入 API Key")
            return
        
        if not self.config.get('listen_friends'):
            messagebox.showwarning("警告", "请填入监听的联系人")
            return
        
        try:
            self.label_status.config(text="启动中...", foreground="orange")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            
            self.bot = AutoReplyBot(self.config)
            self.bot_thread = self.bot.start_async(self._update_status_ui)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
            self.label_status.config(text="启动失败", foreground="red")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
    
    def stop_bot(self):
        """停止机器人"""
        if self.bot:
            self.bot.stop()
            self.bot = None
        
        self.label_status.config(text="已停止", foreground="gray")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
    
    def _update_status_ui(self, message: str):
        """更新 UI 状态"""
        self.label_status.config(text=message, foreground="green")
        self.update_idletasks()
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.bot and self.bot.running:
            if messagebox.askyesno("确认", "机器人正在运行，确认退出？"):
                self.bot.stop()
                self.destroy()
        else:
            self.destroy()


def main():
    """主入口"""
    app = GUIApp()
    app.mainloop()


if __name__ == "__main__":
    main()
