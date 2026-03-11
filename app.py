import gradio as gr
import time
from src.adb_utils import AdbController
from src.agent import VisualAgent, execute_action_on_device
from src.vision import VisionEngine
import cv2
import numpy as np
from PIL import Image

# Global state
class AppState:
    def __init__(self):
        self.adb = AdbController()
        self.agent = VisualAgent(model="minicpm-v")  # Set to minicpm-v as requested
        self.vision = VisionEngine()
        self.running = False
        self.auto_mode = False
        self.pending_action = None
        self.current_task = ""
        self.chat_history = []
        self.latest_screenshot = None
        self.label_map = {}
        self.device_connected = False

app_state = AppState()

def check_connection():
    connected = app_state.adb.check_connection()
    app_state.device_connected = connected
    if connected:
        return "✅ ADB 已连接: 设备在线"
    else:
        return "❌ ADB 未连接: 找不到在线设备"

def draw_action_on_image(image, action_dict):
    """Draw a visual representation of the action on the screenshot."""
    if not image or not action_dict:
        return image

    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    action_type = action_dict.get("type")
    if action_type == "CLICK":
        x, y = action_dict.get("x", 0), action_dict.get("y", 0)
        cv2.circle(img_cv, (x, y), 20, (0, 0, 255), -1)  # Red dot
        cv2.circle(img_cv, (x, y), 25, (0, 255, 255), 3) # Yellow outline
        cv2.putText(img_cv, "CLICK", (x + 30, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    elif action_type == "SWIPE":
        sx, sy = action_dict.get("start_x", 0), action_dict.get("start_y", 0)
        ex, ey = action_dict.get("end_x", 0), action_dict.get("end_y", 0)
        cv2.arrowedLine(img_cv, (sx, sy), (ex, ey), (0, 255, 0), 5, tipLength=0.1) # Green arrow
        cv2.putText(img_cv, "SWIPE", (sx, sy - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    elif action_type == "TYPE":
        text = action_dict.get("text", "")
        h, w = img_cv.shape[:2]
        cv2.putText(img_cv, f"TYPE: {text}", (w//4, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 255), 3)

    return Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))

def refresh_screen(annotate=False):
    if not app_state.device_connected:
        return None
    
    # Save a temporary screenshot for vision processing
    temp_path = "tmp/current_screen.png"
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
        
    screenshot = app_state.adb.get_screenshot()
    screenshot.save(temp_path)
    
    if annotate:
        # Dump UI XML for better element detection
        xml_path = "tmp/view.xml"
        app_state.adb.keyevent("shell uiautomator dump /sdcard/view.xml") # This is a bit hacky via keyevent but let's see
        # Better: use a proper method in adb_utils if it exists, or subprocess
        import subprocess
        subprocess.run([app_state.adb.adb_path, "-s", app_state.adb.device_serial, "shell", "uiautomator", "dump", "/sdcard/view.xml"], capture_output=True)
        subprocess.run([app_state.adb.adb_path, "-s", app_state.adb.device_serial, "pull", "/sdcard/view.xml", xml_path], capture_output=True)
        
        annotated_img, label_map = app_state.vision.get_annotated_screen(temp_path, xml_path=xml_path)
        app_state.label_map = label_map
        app_state.latest_screenshot = annotated_img
        return annotated_img
    
    app_state.latest_screenshot = screenshot
    app_state.label_map = {}
    return screenshot

def step_agent(task, screenshot):
    """Run one step of the agent's decision process."""
    if not screenshot:
        return {"type": "ERROR", "raw": "No screenshot available."}

    action = app_state.agent.get_next_action(task, screenshot, label_map=app_state.label_map)
    return action

def process_loop(task, is_auto, chat_history):
    """The main generator that handles the automatic loop and manual steps."""
    if not task:
        chat_history.append((None, "❌ 请输入任务描述"))
        yield "❌ 请输入任务描述", chat_history, None, gr.update(interactive=False), gr.update(interactive=True)
        return

    # Initialize task state if just starting
    if not app_state.running:
        app_state.current_task = task
        app_state.auto_mode = is_auto
        app_state.running = True
        chat_history.append((task, "开始执行任务..."))

    # Main Loop
    while app_state.running:
        # If there's a pending action and we are NOT in auto mode, we wait for user confirmation.
        if app_state.pending_action and not app_state.auto_mode:
            yield "等待确认...", chat_history, app_state.latest_screenshot, gr.update(interactive=True), gr.update(interactive=False)
            break # Exit the generator, wait for user to click confirm or step

        # 1. Get screenshot
        yield "获取并标注截图中...", chat_history, app_state.latest_screenshot, gr.update(interactive=False), gr.update(interactive=False)
        screenshot = refresh_screen(annotate=True)
        if not screenshot:
            app_state.running = False
            chat_history.append((None, "❌ 获取屏幕截图失败，任务停止。"))
            yield "失败", chat_history, None, gr.update(interactive=False), gr.update(interactive=True)
            return

        # 2. Ask Agent
        chat_history.append((None, "正在请求模型分析..."))
        yield "思考中...", chat_history, screenshot, gr.update(interactive=False), gr.update(interactive=False)

        action_dict = step_agent(app_state.current_task, screenshot)
        app_state.pending_action = action_dict

        # Draw visualization
        annotated_img = draw_action_on_image(screenshot, action_dict)

        msg = f"模型决策: {action_dict.get('raw', 'None')}"
        chat_history.append((None, msg))

        if action_dict.get("type") == "DONE":
            app_state.running = False
            chat_history.append((None, "✅ 任务已完成！"))
            yield "完成", chat_history, annotated_img, gr.update(interactive=False), gr.update(interactive=True)
            return

        if action_dict.get("type") in ["ERROR", "UNKNOWN"]:
            app_state.running = False
            chat_history.append((None, "❌ 解析模型指令失败，任务停止。"))
            yield "失败", chat_history, annotated_img, gr.update(interactive=False), gr.update(interactive=True)
            return

        # 3. Execute Action
        if app_state.auto_mode:
            chat_history.append((None, "自动执行..."))
            yield "执行中...", chat_history, annotated_img, gr.update(interactive=False), gr.update(interactive=False)

            result_msg = execute_action_on_device(action_dict, app_state.adb)
            chat_history.append((None, f"执行结果: {result_msg}"))
            app_state.pending_action = None # Clear pending

            # Short pause after action before the loop repeats
            time.sleep(1)
        else:
            # Manual mode: Pause the loop and wait for confirmation
            yield "等待确认...", chat_history, annotated_img, gr.update(interactive=True), gr.update(interactive=False)
            break # Break loop, user interaction needed


def stop_task(chat_history):
    app_state.running = False
    app_state.pending_action = None
    chat_history.append((None, "🛑 已手动打断任务。"))
    return "任务已打断", chat_history, gr.update(interactive=False), gr.update(interactive=True)

def confirm_action(chat_history):
    if not app_state.pending_action or not app_state.running:
        return "没有等待执行的动作", chat_history, gr.update(interactive=False)

    action_dict = app_state.pending_action
    chat_history.append((None, f"手动确认执行: {action_dict.get('raw')}"))

    result_msg = execute_action_on_device(action_dict, app_state.adb)
    chat_history.append((None, f"执行结果: {result_msg}"))

    app_state.pending_action = None
    time.sleep(1)
    return "执行完毕，请点击下一步继续", chat_history, gr.update(interactive=False)

def resume_step(task, is_auto, chat_history):
    """Used for the Step button in manual mode."""
    # We clear the pending action if we manually step, but we shouldn't have one here usually
    # unless the user wants to ignore the previous and re-analyze.
    app_state.pending_action = None

    # Just restart the process_loop generator logic
    if not app_state.running:
        # If not running, step acts like start
        app_state.running = True
        app_state.current_task = task
        app_state.auto_mode = is_auto
        chat_history.append((task, "开始单步调试..."))

    for output in process_loop(task, is_auto, chat_history):
        yield output

def confirm_action(chat_history):
    if not app_state.pending_action or not app_state.running:
        return "没有等待执行的动作", chat_history, gr.update(interactive=False)

    action_dict = app_state.pending_action
    chat_history.append((None, f"手动确认执行: {action_dict.get('raw')}"))

    result_msg = execute_action_on_device(action_dict, app_state.adb)
    chat_history.append((None, f"执行结果: {result_msg}"))

    app_state.pending_action = None
    time.sleep(1)
    return "执行完毕，准备下一步", chat_history, gr.update(interactive=False)

def clear_chat():
    return []

# --- Gradio UI Definition ---
with gr.Blocks(title="Android Vision Agent") as demo:
    gr.Markdown("# 📱 基于本地视觉模型的 Android 自动化操作助手")

    with gr.Row():
        with gr.Column(scale=1):
            conn_status = gr.Markdown("⏳ 检查设备连接中...")
            conn_btn = gr.Button("🔄 刷新设备连接", size="sm")

            gr.Markdown("### 任务配置")
            task_input = gr.Textbox(label="输入您想让设备完成的任务", placeholder="例如：打开设置，搜索'显示'，然后返回主页", lines=2)
            auto_checkbox = gr.Checkbox(label="开启全自动模式 (不勾选则每次操作前需要手动确认)", value=False)

            with gr.Row():
                start_btn = gr.Button("🚀 开始执行", variant="primary")
                step_btn = gr.Button("⏭️ 下一步 (执行分析)", variant="secondary")
                stop_btn = gr.Button("🛑 停止/打断", variant="stop")

            status_text = gr.Textbox(label="当前状态", interactive=False)
            confirm_btn = gr.Button("✅ 确认执行当前分析出的操作", variant="primary", interactive=False)

            gr.Markdown("### 执行日志")
            chatbot = gr.Chatbot(label="对话与记录", height=400)
            clear_btn = gr.Button("🗑️ 清空记录", size="sm")

        with gr.Column(scale=1):
            gr.Markdown("### 实时画面")
            refresh_screen_btn = gr.Button("📷 手动刷新画面")
            screen_display = gr.Image(label="安卓设备屏幕 (带操作标注)", interactive=False, type="pil")

    # Callbacks
    conn_btn.click(fn=check_connection, outputs=[conn_status])
    demo.load(fn=check_connection, outputs=[conn_status])

    refresh_screen_btn.click(fn=lambda: refresh_screen(annotate=True), outputs=[screen_display])
    clear_btn.click(fn=clear_chat, outputs=[chatbot])

    start_btn.click(
        fn=process_loop,
        inputs=[task_input, auto_checkbox, chatbot],
        outputs=[status_text, chatbot, screen_display, confirm_btn, start_btn]
    )

    step_btn.click(
        fn=resume_step,
        inputs=[task_input, auto_checkbox, chatbot],
        outputs=[status_text, chatbot, screen_display, confirm_btn, start_btn]
    )

    stop_btn.click(
        fn=stop_task,
        inputs=[chatbot],
        outputs=[status_text, chatbot, confirm_btn, start_btn]
    )

    confirm_btn.click(
        fn=confirm_action,
        inputs=[chatbot],
        outputs=[status_text, chatbot, confirm_btn]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())
