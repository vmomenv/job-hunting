# 环境搭建指南 (Environment Setup)

本项目依赖真实安卓设备、ADB 工具和本地 Python 环境。以下是详细配置步骤。

## 1. 真实安卓设备 (Physical Android Device) 配置
1.  **开启开发者选项**：在手机“设置” -> “关于手机” -> 连续点击“版本号” (或“软件信息”中的版本号) 直到提示已开启开发者模式。
2.  **开启 USB 调试**：进入“系统/附加设置” -> “开发者选项”，开启“USB 调试”。
3.  **开启模拟点击**（关键）：部分品牌（如小米、OPPO、VIVO）需额外开启“USB 调试（安全设置）”，否则 ADB 无法发送点击 and 滑动指令。
4.  **连接电脑**：使用数据线连接手机与电脑，手机弹出调试授权时选择“始终允许”。

## 2. Windows 本地 ADB 工具
1.  确保已安装 [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools)。
2.  将 `platform-tools` 路径添加到系统环境变量 `Path` 中。
3.  **连接确认**：
    在终端输入 `adb devices`，应能看到形如 `866... device` 的设备序列号。

## 3. 本地视觉模型安装 (Vision Model)
推荐使用 **Ollama** 运行多模态大模型 (VLM)。

### 使用 Ollama (推荐)
1.  安装 [Ollama](https://ollama.com/download)。
2.  **拉取视觉模型**：
    ```bash
    ollama run llama3-vision:8b  # 或者使用 llava, ovis 等
    ```
3.  Ollama 默认在 `localhost:11434` 提供 API。

## 4. Python 项目初始化
1.  在项目根目录下创建虚拟环境：
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
2.  安装依赖：
    ```bash
    pip install pandas openpyxl pillow requests
    ```

## 5. 配置期望
在 `config.yaml` 中设置您的目标岗位和待遇要求，脚本将以此为依据进行筛选。
