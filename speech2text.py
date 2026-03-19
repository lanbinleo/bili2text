import whisper
import os

whisper_model = None

def is_cuda_available():
    return whisper.torch.cuda.is_available()

def load_whisper(model="tiny"):
    global whisper_model
    whisper_model = whisper.load_model(model, device="cuda" if is_cuda_available() else "cpu")
    print("Whisper模型："+model)

def run_analysis_in_memory(chunks, prompt="以下是普通话的句子。"):
    """直接接收 numpy 数组列表进行转录，返回完整文本字符串，不读写任何文件。"""
    global whisper_model
    full_text = []
    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        print(f"正在转换第{i}/{total}个音频...")
        result = whisper_model.transcribe(chunk, initial_prompt=prompt)
        text = "".join([s["text"] for s in result["segments"] if s])
        print(text)
        full_text.append(text)
    return "\n".join(full_text)

def run_analysis(filename, model="tiny", prompt="以下是普通话的句子。"):
    print("正在加载Whisper模型...")
    # 读取列表中的音频文件
    audio_list = os.listdir(f"audio/slice/{filename}")
    print("加载Whisper模型成功！")
    # 添加排序逻辑
    audio_files = sorted(
        audio_list,
        key=lambda x: int(os.path.splitext(x)[0])  # 按文件名数字排序
    )
    # 创建outputs文件夹
    os.makedirs("outputs", exist_ok=True)
    print("正在转换文本...")

    audio_list.sort(key=lambda x: int(x.split(".")[0])) # 将 audio_list 按照切片序号排序

    i = 1
    for fn in audio_files:
        print(f"正在转换第{i}/{len(audio_files)}个音频... {fn}")
        # 识别音频
        result = whisper_model.transcribe(f"audio/slice/{filename}/{fn}", initial_prompt=prompt)
        print("".join([i["text"] for i in result["segments"] if i is not None]))

        with open(f"outputs/{filename}.txt", "a", encoding="utf-8") as f:
            f.write("".join([i["text"] for i in result["segments"] if i is not None]))
            f.write("\n")
        i += 1
    