<p align="center">
  <img src="light_logo2.png" alt="bili2text logo" width="400"/>
</p>


<p align="center">
    <img src="https://img.shields.io/github/stars/lanbinshijie/bili2text" alt="GitHub stars"/>
    <img src="https://img.shields.io/github/license/lanbinshijie/bili2text" alt="GitHub"/>
    <img src="https://img.shields.io/github/last-commit/lanbinshijie/bili2text" alt="GitHub last commit"/>
    <img src="https://img.shields.io/github/v/release/lanbinshijie/bili2text" alt="GitHub release (latest by date)"/>
</p>

# Bili2text 📺

## 转移说明
因为作者的旧账号（lanbinshijie）已经停用，仓库已经转移到新账号（lanbinleo）

感谢各位的支持，如果有任何想法欢迎在issue中提出，或者提交pr~

v2版本开发进度，请查看dev分支；v3版本更名为v2版本

![alt text](./assets/new_v_sc.png)

## 简介 🌟
bili2text 是一个用于将 Bilibili 视频转换为文本的工具🛠️。这个项目通过一个简单的流程实现：下载视频、提取音频、分割音频，并使用 whisper 模型将语音转换为文本。整个过程是自动的，只需输入 Bilibili 视频的 av 号即可。整个过程行云流水，一步到胃😂

## 功能 🚀
- 🎥**下载视频**：从 Bilibili 下载指定的视频，支持多P视频的下载。
- 🎵**提取音频**：从下载的视频中提取音频。
- 💬**音频分割**：将音频分割成小段，以便于进行高效的语音转文字处理。
- 🤖**语音转文字**：使用 OpenAI 的 whisper 模型将音频转换为文本。

## 使用方法 📘
1. **克隆仓库**：
   ```bash
   git clone https://github.com/lanbinleo/bili2text.git
   cd bili2text
   ```

2. **安装依赖**：
   安装必要的 Python 库。
   ```bash
   pip install -r requirements.txt
   ```

3. **创建桌面快捷方式（推荐）**：
   双击运行项目根目录下的 `create_shortcut.bat`，会自动在桌面创建 **Bili2Text** 快捷图标。之后每次只需双击桌面图标即可启动。

   > 如提示权限不足，请右键选择"以管理员身份运行"。

4. **直接启动（命令行）**：
   双击根目录下的 `start.bat`，或在终端中执行：
   ```bash
   python window.py
   ```
   在弹出的窗口中粘贴 Bilibili 视频链接，加载 Whisper 模型后点击生成即可。

## 示例 📋
```python
from downBili import download_video
from exAudio import *
from speech2text import *

av = input("请输入av号：")
filename = download_video(av)
foldername = run_split(filename)
run_analysis(foldername, prompt="以下是普通话的句子。这是一个关于{}的视频。".format(filename))
output_path = f"outputs/{foldername}.txt"
print("转换完成！", output_path)
```

## 技术栈 🧰
- [Python](https://www.python.org/) 主要编程语言，负责实现程序逻辑功能
- [Whisper](https://github.com/openai/whisper) 语音转文字模型
- [Tkiner](https://docs.python.org/3/library/tkinter.html) UI界面展示相关工具
- [TTKbootstrap](https://ttkbootstrap.readthedocs.io/en/latest/zh/) UI界面美化库

## 后续开发计划 📅

- [X] 生成requirements.txt
- [X] UI化设计


## 运行截图 📷
<!-- assets/screenshot1.png -->
<img src="assets/screenshot3.png" alt="screenshot3" width="600"/>
<img src="assets/screenshot2.png" alt="screenshot2" width="600"/>
<img src="assets/screenshot1.png" alt="screenshot1" width="600"/>

## Star History ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=lanbinshijie/bili2text&type=Date)](https://star-history.com/#lanbinshijie/bili2text&Date)



## 许可证 📄
本项目根据 MIT 许可证发布。

## 贡献 💡
如果你想为这个项目做出贡献，欢迎提交 Pull Request 或创建 Issue。

## 投喂一下！

> TKTg2T7u7xdV4xDAzbzird2qmWoqLanbin

![image](https://github.com/user-attachments/assets/412470b8-7fd5-4632-a085-9c48a9d5e18b)

TRC20链！谢谢大家！

## 致谢 🙏
再此感谢Open Teens对青少年开源社区做出的贡献！[@OpenTeens](https://openteens.org)

## 使用须知 🖥️

**用户在使用 bili2text 工具时，必须遵守用户所在地区的相关版权法律和规定。请确保您有权利下载和转换的视频内容，尊重创作者的劳动成果。**

