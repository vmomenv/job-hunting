# 环境搭建指南 (Environment Setup)

本项目依赖雷电模拟器、ADB 工具和本地 Python 环境。以下是详细配置步骤。

## 1. 安卓设备 (Android Device) 配置
1.  **开启开发者选项**：在手机“设置” -> “关于手机” -> 连续点击“版本号”直到开启。
2.  **开启 USB 调试**：进入“系统” -> “开发者选项”，开启“USB 调试”。
3.  **开启模拟点击**（部分机型如小米）：开启“USB 调试（安全设置）”，否则脚本无法点击。
4.  (可选) 建议关闭屏幕休眠或设置为长时间开启。

## 2. Windows 本地 ADB 工具
1.  下载 [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)。
2.  解压并将文件夹路径添加到 Windows 系统环境变量 `Path` 中。
3.  **连接确认**：
    在终端输入 `adb devices`，应能看到模拟器的 IP:端口 (通常是 `127.0.0.1:5555`)。

## 3. 本地视觉模型安装 (Vision Model)
推荐使用 **Ollama** 或 **MiniCPM-V** 完成本地识别。

### 方案 A：使用 Ollama (推荐 - 易于管理)
1.  安装 [Ollama](https://ollama.com/download)。
2.  **拉取视觉模型**：
    ```bash
    ollama run llama3-vision:8b  # 或者使用更轻量的 moondream
    ```
3.  Ollama 会提供一个本地 API (默认 `localhost:11434`)，供 Python 脚本调用发送截图。

### 方案 B：本地 Python 推理 (性能更高)
1.  安装 CUDA 环境 (对于 NVIDIA 显卡)。
2.  安装相关库：
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    pip install transformers pillow paddleocr
    ```

## 4. Python 项目初始化
1.  在项目根目录下创建虚拟环境：
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
2.  安装依赖：
    ```bash
    pip install pandas openpyxl uiautomator2
    ```

## 5. 准备简历
将您的简历 (PDF 格式) 放置在项目根目录下的 `data/resume.pdf`，脚本后续将基于此进行分析。
