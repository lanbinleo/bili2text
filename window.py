import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import webbrowser
import re
import os
import glob as _glob
import sys
import threading
from utils import download_video
from exAudio import convert_flv_to_mp3, split_mp3, process_audio_split

speech_to_text = None  # 模型实例

def is_cuda_available(whisper):
    return whisper.torch.cuda.is_available()

def open_popup(text, title="提示"):

    popup = ttk.Toplevel()
    popup.title(title)
    popup.geometry("300x150")
    popup.update_idletasks()
    x = (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2
    y = (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2
    popup.geometry("+%d+%d" % (x, y))
    label = ttk.Label(popup, text=text)
    label.pack(pady=10)
    user_choice = ttk.StringVar()

    def on_confirm():
        user_choice.set("confirmed")
        popup.destroy()
    confirm_button = ttk.Button(popup, text="确定", style="primary.TButton", command=on_confirm)
    confirm_button.pack(side=LEFT, padx=10, pady=10)

    def on_cancel():
        user_choice.set("cancelled")
        popup.destroy()
    cancel_button = ttk.Button(popup, text="取消", style="outline-danger.TButton", command=on_cancel)
    cancel_button.pack(side=RIGHT, padx=10, pady=10)
    popup.wait_window()
    return user_choice.get()

def show_log(text, state="INFO"):

    log_text.config(state="normal")
    log_text.insert(END, f"[LOG][{state}] {text}\n")
    log_text.config(state="disabled")

def on_url_change(*_):
    text = video_link_entry.get()
    if re.search(r'BV[A-Za-z0-9]+', text):
        generate_button.config(state=NORMAL)
    else:
        generate_button.config(state=DISABLED)

def on_generate_click():
    global speech_to_text
    if speech_to_text is None:
        print("Whisper未加载！请点击加载Whisper按钮。")
        return
    video_link = video_link_entry.get()
    matches = re.findall(r'BV[A-Za-z0-9]+', video_link)
    bv_number = matches[0]
    video_files = _glob.glob(f"bilibili_video/{bv_number}/*.mp4")
    skip_download = len(video_files) > 0
    if skip_download:
        msg = f"检测到本地缓存（{bv_number}），直接生成文本？"
    else:
        msg = "是否确定生成？需要先下载视频，可能耗费时间较长"
    if open_popup(msg, title="提示") == "cancelled":
        return
    print(f"BV号: {bv_number}，{'使用本地缓存' if skip_download else '下载视频'}")
    thread = threading.Thread(target=process_video, args=(bv_number, skip_download))
    thread.start()

def process_video(bv_number, skip_download=False):
    print("=" * 10)
    if skip_download:
        print(f"检测到本地缓存，跳过下载...")
        file_identifier = bv_number
    else:
        print("正在下载视频...")
        file_identifier = download_video(bv_number[2:])  # download_video 接受不带 BV 前缀的号
    print("=" * 10)
    print("正在分割音频...")
    folder_name = process_audio_split(file_identifier)
    print("=" * 10)
    print("正在转换文本（可能耗时较长）...")
    speech_to_text.run_analysis(folder_name,
        prompt="以下是普通话的句子。这是一个关于{}的视频。".format(file_identifier))
    output_path = f"outputs/{folder_name}.txt"
    print("转换完成！", output_path)


def on_clear_log_click():
    # 临时恢复原始 stdout/stderr，避免清空期间的输出被重定向回 log_text
    try:
        sys.stdout = _orig_stdout
        sys.stderr = _orig_stderr
    except NameError:
        # 如果还没初始化原始对象，跳过
        pass
    try:
        log_text.config(state="normal")
        log_text.delete('1.0', END)
        log_text.config(state="disabled")
    finally:
        # 重新启用重定向（如果之前启用了）
        try:
            redirect_system_io()
        except Exception:
            # 避免在清空日志时抛出异常导致界面卡住
            pass

def load_whisper_model():
    global speech_to_text
    import speech2text
    speech_to_text = speech2text
    current_model = model_var.get()
    speech_to_text.load_whisper(model=current_model)
    msg = "CUDA加速已启用" if is_cuda_available(speech_to_text.whisper) else "使用CPU计算"
    print(f"加载Whisper成功！模型：{current_model}，{msg}")
    try:
        model_status_label.config(text=f"当前模型：{current_model}", foreground="green")
    except Exception:
        pass

def open_github_link(event=None):
    webbrowser.open_new("https://github.com/lanbinshijie/bili2text")

def redirect_system_io():
    global _orig_stdout, _orig_stderr
    # 仅在首次调用时保存原始 stdout/stderr
    if '_orig_stdout' not in globals():
        _orig_stdout = sys.stdout
        _orig_stderr = sys.stderr

    class StdoutRedirector:
        def __init__(self):
            self._buffer = ""
        def write(self, message, state="INFO"):
            if not message:
                return
            # 跳过进度信息
            if "Speed" in message:
                return
            self._buffer += message
            # 只在遇到换行时写入完整行，避免把片段拆成多行日志
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                if line.strip():
                    try:
                        log_text.config(state="normal")
                        log_text.insert(END, f"[LOG][{state}] {line}\n")
                        log_text.config(state="disabled")
                        log_text.see(END)
                    except Exception:
                        # 如果 UI 还没准备好，回退写到原始 stdout，避免丢失日志或递归
                        try:
                            _orig_stdout.write(line + "\n")
                        except Exception:
                            pass
        def flush(self):
            if self._buffer.strip():
                try:
                    log_text.config(state="normal")
                    log_text.insert(END, f"[LOG][INFO] {self._buffer}\n")
                    log_text.config(state="disabled")
                    log_text.see(END)
                except Exception:
                    try:
                        _orig_stdout.write(self._buffer + "\n")
                    except Exception:
                        pass
            self._buffer = ""

    # 安装重定向器
    sys.stdout = StdoutRedirector()
    sys.stderr = StdoutRedirector()

def select_and_load_whisper():
    """打开模型选择弹窗，选中后加载"""
    popup = ttk.Toplevel()
    popup.title("选择Whisper模型")
    popup.geometry("360x180")
    popup.resizable(False, False)
    popup.update_idletasks()
    x = (popup.winfo_screenwidth() - popup.winfo_reqwidth()) // 2
    y = (popup.winfo_screenheight() - popup.winfo_reqheight()) // 2
    popup.geometry("+%d+%d" % (x, y))

    ttk.Label(popup, text="请选择要加载的模型：", font=("Helvetica", 11)).pack(pady=(18, 10))

    selected_model = ttk.StringVar(value=model_var.get())
    model_buttons = {}

    def select_model(m):
        selected_model.set(m)
        for name, btn in model_buttons.items():
            btn.config(bootstyle="primary" if name == m else "outline-secondary")

    btn_frame = ttk.Frame(popup)
    btn_frame.pack()
    for model_name in ["tiny", "small", "medium", "large"]:
        style = "primary" if model_name == selected_model.get() else "outline-secondary"
        btn = ttk.Button(btn_frame, text=model_name, bootstyle=style, width=7,
                         command=lambda m=model_name: select_model(m))
        btn.pack(side=LEFT, padx=6)
        model_buttons[model_name] = btn

    confirmed = [False]

    def on_confirm():
        confirmed[0] = True
        popup.destroy()

    ttk.Button(popup, text="加载", bootstyle="success", width=10, command=on_confirm).pack(pady=16)

    popup.wait_window()

    if confirmed[0]:
        model_var.set(selected_model.get())
        load_whisper_model()


def main():
    global video_link_entry, log_text, model_var, model_status_label, generate_button
    app = ttk.Window("Bili2Text - By Lanbin | www.lanbin.top", themename="litera")
    app.geometry("820x540")
    app.iconbitmap("favicon.ico")
    ttk.Label(app, text="Bilibili To Text", font=("Helvetica", 16)).pack(pady=10)

    input_box = ttk.LabelFrame(app, text="视频生成", padding=10)
    input_box.pack(fill=X, padx=20, pady=(0, 8))

    whisper_frame = ttk.Frame(input_box)
    load_whisper_button = ttk.Button(whisper_frame, text="加载Whisper", command=select_and_load_whisper, bootstyle="success-outline")
    load_whisper_button.pack(side=LEFT, padx=(0, 8))
    model_status_label = ttk.Label(whisper_frame, text="未加载", foreground="gray")
    model_status_label.pack(side=LEFT)
    whisper_frame.pack(fill=X, pady=(0, 6))

    video_link_frame = ttk.Frame(input_box)
    video_link_var = ttk.StringVar()
    video_link_var.trace_add("write", on_url_change)
    video_link_entry = ttk.Entry(video_link_frame, textvariable=video_link_var)
    video_link_entry.pack(side=LEFT, expand=YES, fill=X)
    generate_button = ttk.Button(video_link_frame, text="生成", command=on_generate_click, state=DISABLED)
    generate_button.pack(side=RIGHT, padx=(8, 0))
    video_link_frame.pack(fill=X)

    log_box = ttk.LabelFrame(app, text="日志", padding=10)
    log_box.pack(fill=BOTH, expand=YES, padx=20, pady=(0, 8))

    clear_log_button = ttk.Button(log_box, text="清空日志", command=on_clear_log_click, bootstyle=DANGER)
    clear_log_button.pack(anchor=E, pady=(0, 4))

    log_text = ttk.ScrolledText(log_box, height=10, state="disabled")
    log_text.pack(fill=BOTH, expand=YES)

    model_var = ttk.StringVar(value="small")
    
    footer_frame = ttk.Frame(app)
    footer_frame.pack(side=BOTTOM, fill=X)
    author_label = ttk.Label(footer_frame, text="作者：Lanbin")
    author_label.pack(side=LEFT, padx=10, pady=10)
    version_var = ttk.StringVar(value="2.0.0")
    version_label = ttk.Label(footer_frame, text="版本 " + version_var.get(), foreground="gray")
    version_label.pack(side=LEFT, padx=10, pady=10)
    github_link = ttk.Label(footer_frame, text="开源仓库", cursor="hand2", bootstyle=PRIMARY)
    github_link.pack(side=LEFT, padx=10, pady=10)
    github_link.bind("<Button-1>", open_github_link)
    
    redirect_system_io()
    app.mainloop()

if __name__ == "__main__":
    main()
