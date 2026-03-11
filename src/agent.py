import requests
import base64
from io import BytesIO
from PIL import Image
import json
import re
import math

class VisualAgent:
    def __init__(self, ollama_url="http://localhost:11434/api/generate", model="minicpm-v"):
        """Initialize the agent with Ollama configuration."""
        self.ollama_url = ollama_url
        self.model = model
        self.history = []
        self.target_max_size = 1024 # Scale images down to save VRAM

    def _resize_and_encode_image(self, image):
        """Resize the image while maintaining aspect ratio, then base64 encode it."""
        original_width, original_height = image.size
        scale = 1.0

        if max(original_width, original_height) > self.target_max_size:
            scale = self.target_max_size / max(original_width, original_height)
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            resized_image = image

        # Encode to Base64
        buffered = BytesIO()
        resized_image.save(buffered, format="JPEG") # Use JPEG for smaller size over API
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return img_str, scale

    def create_prompt(self, task_description):
        """Build the system prompt for the model."""
        prompt = f"""
You are a helpful AI assistant controlling an Android smartphone to complete a specific task for the user.
The task is: "{task_description}"

You are given a screenshot of the current Android device screen. Some elements on the screen may have numeric labels (e.g., a "1" in a red box next to an icon). 
Analyze the screen and decide the next single action to take. 
You must output ONLY ONE action from the list below. Do not provide any explanation, just the action command.

Valid Actions:
1. CLICK [label]
   - Use this to tap on an element that has a numeric label. 
   - Example: CLICK [5] (taps on the element marked with label 5)
2. CLICK [x, y]
   - Use this to tap on a specific location if no label is available. x and y are the coordinates as a percentage of the screen width and height (0-100).
   - Example: CLICK [50, 75] 
3. SWIPE [start_label] TO [end_label] or SWIPE [start_x, start_y] TO [end_x, end_y]
   - Use this to scroll or swipe. 
   - Example: SWIPE [50, 80] TO [50, 20] 
4. TYPE "text"
   - Use this to input text. Ensure you have clicked a text box before typing.
   - Example: TYPE "Hello world"
5. BACK
   - Use this to press the physical back button on Android.
6. HOME
   - Use this to press the physical home button.
7. DONE
   - Use this when the task is fully completed.

Your response must be exactly one of these commands. Do not write anything else.
Action: """
        return prompt

    def get_next_action(self, task_description, current_screenshot, label_map=None):
        """Send the current state to Ollama and get the next action."""
        self.label_map = label_map or {}

        # Prepare image
        encoded_image, scale = self._resize_and_encode_image(current_screenshot)

        # Prepare prompt
        prompt = self.create_prompt(task_description)

        # Construct payload for Ollama
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False,
            "options": {
                "temperature": 0.1, # Keep temperature low for more deterministic output
                "num_ctx": 4096
            }
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=60)
            response.raise_for_status()
            result_json = response.json()
            raw_action = result_json.get("response", "").strip()

            # Record in history
            self.history.append({"task": task_description, "action": raw_action})

            return self.parse_action(raw_action, current_screenshot.size)

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Ollama: {e}")
            return {"type": "ERROR", "message": str(e), "raw": ""}

    def parse_action(self, raw_action, screen_size):
        """
        Parse the string output from the LLM into a structured action dictionary.
        Convert percentage coordinates back to pixel coordinates based on the original screen size.
        """
        width, height = screen_size

        def pct_to_px(pct_x, pct_y):
            # pct comes in as 0-100
            px = int((float(pct_x) / 100.0) * width)
            py = int((float(pct_y) / 100.0) * height)
            # Bound coordinates
            px = max(0, min(px, width - 1))
            py = max(0, min(py, height - 1))
            return px, py

        # 1. CLICK [label] or CLICK [x, y]
        label_click = re.match(r'^CLICK\s*\[\s*(\d+)\s*\]', raw_action, re.IGNORECASE)
        if label_click:
            label_id = label_click.group(1)
            if label_id in self.label_map:
                px, py = self.label_map[label_id]
                return {"type": "CLICK", "x": px, "y": py, "raw": raw_action, "label": label_id}

        click_match = re.match(r'^CLICK\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', raw_action, re.IGNORECASE)
        if click_match:
            pct_x, pct_y = click_match.groups()
            px, py = pct_to_px(pct_x, pct_y)
            return {"type": "CLICK", "x": px, "y": py, "raw": raw_action}

        # 2. SWIPE [start_x, start_y] TO [end_x, end_y]
        swipe_match = re.match(r'^SWIPE\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]\s*TO\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]', raw_action, re.IGNORECASE)
        if swipe_match:
            sx, sy, ex, ey = swipe_match.groups()
            start_px, start_py = pct_to_px(sx, sy)
            end_px, end_py = pct_to_px(ex, ey)
            return {
                "type": "SWIPE",
                "start_x": start_px, "start_y": start_py,
                "end_x": end_px, "end_y": end_py,
                "raw": raw_action
            }

        # 3. TYPE "text"
        type_match = re.match(r'^TYPE\s+"(.*?)"', raw_action, re.IGNORECASE)
        if type_match:
            text = type_match.group(1)
            return {"type": "TYPE", "text": text, "raw": raw_action}

        # 4. BACK
        if re.search(r'\bBACK\b', raw_action, re.IGNORECASE):
            return {"type": "BACK", "raw": raw_action}

        # 5. HOME
        if re.search(r'\bHOME\b', raw_action, re.IGNORECASE):
            return {"type": "HOME", "raw": raw_action}

        # 6. DONE
        if re.search(r'\bDONE\b', raw_action, re.IGNORECASE):
            return {"type": "DONE", "raw": raw_action}

        # Fallback if the model didn't follow the format strictly
        return {"type": "UNKNOWN", "raw": raw_action}

def execute_action_on_device(action_dict, adb_controller):
    """Takes the parsed action dictionary and executes it via adb_utils."""
    action_type = action_dict.get("type")

    if action_type == "CLICK":
        adb_controller.tap(action_dict["x"], action_dict["y"])
        return f"Clicked at ({action_dict['x']}, {action_dict['y']})"

    elif action_type == "SWIPE":
        adb_controller.swipe(
            action_dict["start_x"], action_dict["start_y"],
            action_dict["end_x"], action_dict["end_y"]
        )
        return f"Swiped from ({action_dict['start_x']}, {action_dict['start_y']}) to ({action_dict['end_x']}, {action_dict['end_y']})"

    elif action_type == "TYPE":
        adb_controller.input_text(action_dict["text"])
        # Also simulate pressing ENTER after typing
        adb_controller.press_enter()
        return f"Typed: '{action_dict['text']}'"

    elif action_type == "BACK":
        adb_controller.press_back()
        return "Pressed BACK button"

    elif action_type == "HOME":
        adb_controller.press_home()
        return "Pressed HOME button"

    elif action_type == "DONE":
        return "Task Completed."

    else:
        return f"Unknown or invalid action: {action_dict.get('raw', 'No output')}"
