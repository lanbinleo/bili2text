from utils import download_video
from exAudio import *
from speech2text import *

# Main文件是作者用来测试的，请运行window.py

av = input("请输入BV号：")
filename = download_video(av[2:])
foldername = process_audio_split(filename)


load_whisper("small")
run_analysis(foldername, prompt="以下是普通话的句子。")
output_path = f"outputs/{foldername}.txt"
print("转换完成！", output_path)
