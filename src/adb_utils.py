import subprocess
from PIL import Image
import io
import time
import re
import os
import yaml

def get_adb_path(config=None):
    """Dynamically find the ADB executable path."""
    if config and config.get("device", {}).get("adb_path"):
        adb_path = config["device"]["adb_path"]
        if os.path.exists(adb_path):
            return adb_path

    # Check common environment variables
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home:
        # Check standard SDK paths
        paths_to_check = [
            os.path.join(android_home, "platform-tools", "adb"),
            os.path.join(android_home, "platform-tools", "adb.exe"),
        ]
        for p in paths_to_check:
            if os.path.exists(p):
                return p

    # Fallback to system path (assuming it's in PATH)
    return "adb"


class AdbController:
    def __init__(self, device_serial=None):
        self.config = self._load_config()
        self.adb_path = get_adb_path(self.config)
        self.device_serial = device_serial or self.config.get("device", {}).get("device_serial")

        # Connect to Wi-Fi device if configured and no specific serial is provided yet
        if not self.device_serial:
            wifi_ip = self.config.get("device", {}).get("wifi_device_ip")
            if wifi_ip:
                print(f"Attempting to connect to Wi-Fi device at {wifi_ip}...")
                self._connect_wifi(wifi_ip)
                self.device_serial = wifi_ip

        # Determine the adb command prefix based on whether a specific serial is provided
        self.adb_cmd_prefix = [self.adb_path]
        if self.device_serial:
            self.adb_cmd_prefix.extend(["-s", self.device_serial])

        self.width = None
        self.height = None
        self._get_resolution()

    def _load_config(self):
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _connect_wifi(self, ip_address):
        """Connect to device over Wi-Fi."""
        try:
            subprocess.run([self.adb_path, "connect", ip_address], check=True, capture_output=True, text=True)
            time.sleep(1) # Give it a second to connect
        except Exception as e:
            print(f"Error connecting to Wi-Fi device {ip_address}: {e}")

    def get_devices(self):
        """Get a list of connected devices."""
        try:
            result = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split("\n")[1:]
            devices = [line.split("\t")[0] for line in lines if "device" in line and "offline" not in line]
            return devices
        except Exception as e:
            print("Error getting adb devices:", e)
            return []

    def _get_resolution(self):
        """Retrieve device screen resolution via adb."""
        cmd = self.adb_cmd_prefix + ["shell", "wm", "size"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            # Expected output format: "Physical size: 1080x2400"
            match = re.search(r"(\d+)x(\d+)", output)
            if match:
                self.width = int(match.group(1))
                self.height = int(match.group(2))
            else:
                print("Warning: Could not parse resolution from:", output)
        except Exception as e:
            print("Error retrieving resolution:", e)

    def check_connection(self):
        """Check if the ADB device is connected."""
        devices = self.get_devices()
        if self.device_serial:
            return self.device_serial in devices
        elif devices:
            # Auto-select the first device if none is specified and multiple are present
            if len(devices) > 1:
                print(f"Multiple devices found: {devices}. Auto-selecting {devices[0]}")
            self.device_serial = devices[0]
            self.adb_cmd_prefix = [self.adb_path, "-s", self.device_serial]
            # re-fetch resolution for the newly selected device
            self._get_resolution()
            return True
        return False

    def get_screenshot(self):
        """Capture screenshot from the device and return as PIL Image."""
        cmd = self.adb_cmd_prefix + ["exec-out", "screencap", "-p"]
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            # The output is a PNG image in bytes
            image_data = result.stdout
            image = Image.open(io.BytesIO(image_data))
            return image
        except Exception as e:
            print("Error getting screenshot:", e)
            # Return a blank image as fallback
            return Image.new('RGB', (1080, 1920), color='black')

    def tap(self, x, y):
        """Simulate a tap at (x, y)."""
        cmd = self.adb_cmd_prefix + ["shell", "input", "tap", str(int(x)), str(int(y))]
        try:
            subprocess.run(cmd, check=True)
            time.sleep(0.5) # Small delay after tapping
            return True
        except Exception as e:
            print("Error tapping:", e)
            return False

    def swipe(self, start_x, start_y, end_x, end_y, duration_ms=500):
        """Simulate a swipe from (start_x, start_y) to (end_x, end_y)."""
        cmd = self.adb_cmd_prefix + [
            "shell", "input", "swipe",
            str(int(start_x)), str(int(start_y)),
            str(int(end_x)), str(int(end_y)),
            str(duration_ms)
        ]
        try:
            subprocess.run(cmd, check=True)
            time.sleep(0.5)
            return True
        except Exception as e:
            print("Error swiping:", e)
            return False

    def input_text(self, text):
        """Input text on the device. Escapes special characters for adb shell."""
        # Escape special characters that could mess up the shell execution
        # ADB shell requires certain characters to be escaped.
        # Enclose the text in single quotes to treat it literally, and escape single quotes if present.
        text = str(text).replace("'", "''")
        # Additionally, some devices need spaces replaced by %s depending on the shell, but using single quotes usually suffices.
        formatted_text = f"'{text}'"

        cmd = self.adb_cmd_prefix + ["shell", "input", "text", formatted_text]
        try:
            subprocess.run(cmd, check=True)
            time.sleep(0.5)
            return True
        except Exception as e:
            print("Error inputting text:", e)
            return False

    def keyevent(self, keycode):
        """Simulate a physical key event."""
        cmd = self.adb_cmd_prefix + ["shell", "input", "keyevent", str(keycode)]
        try:
            subprocess.run(cmd, check=True)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"Error sending keyevent {keycode}:", e)
            return False

    def press_back(self):
        """Press the hardware back button."""
        return self.keyevent("4") # KEYCODE_BACK = 4

    def press_home(self):
        """Press the hardware home button."""
        return self.keyevent("3") # KEYCODE_HOME = 3

    def press_enter(self):
        """Press the Enter/Search key."""
        return self.keyevent("66") # KEYCODE_ENTER = 66
