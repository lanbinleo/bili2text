from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import os
import time
import subprocess

def check_video_integrity(file_path):
    """使用 FFmpeg 验证视频文件完整性"""
    result = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-'],
        stderr=subprocess.PIPE,
        text=True
    )
    if result.stderr:
        print(f"视频文件可能损坏: {file_path}")
        print(f"FFmpeg 错误信息: {result.stderr}")
        return False
    return True

def convert_flv_to_mp3(name, target_name=None, folder='bilibili_video'):
    input_path = f'{folder}/{name}.mp4'  
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"视频文件不存在: {input_path}")
    if not check_video_integrity(input_path):
        raise ValueError(f"视频文件损坏: {input_path}")
    # 提取视频中的音频并保存为 MP3 到 audio/conv 目录
    clip = VideoFileClip(input_path)
    audio = clip.audio
    os.makedirs("audio/conv", exist_ok=True)
    output_name = target_name if target_name else name
    audio.write_audiofile(f"audio/conv/{output_name}.mp3")

def split_mp3(filename, folder_name, slice_length=45000, target_folder="audio/slice"):
    audio = AudioSegment.from_mp3(filename)
    total_slices = (len(audio)+ slice_length - 1) // slice_length
    target_dir = os.path.join(target_folder, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    for i in range(total_slices):
        start = i * slice_length
        end = start + slice_length
        slice_audio = audio[start:end]
        slice_path = os.path.join(target_dir, f"{i+1}.mp3")
        slice_audio.export(slice_path, format="mp3")
        print(f"Slice {i+1} saved: {slice_path}")

def process_audio_split(name):
    # 生成唯一文件夹名，并依次调用转换和分割函数
    folder_name = time.strftime('%Y%m%d%H%M%S')
    convert_flv_to_mp3(name, target_name=folder_name)
    conv_dir = f"audio/conv/{folder_name}"
    split_mp3(conv_dir, folder_name)
    return folder_name

