import subprocess
import os
import re
import time
from src.adb_utils import AdbController

class DeviceController:
    def __init__(self, serial=None):
        self.adb = AdbController(device_serial=serial)
        # Expose serial for backwards compatibility in main.py
        self.serial = self.adb.device_serial
        self.width = self.adb.width or 1080
        self.height = self.adb.height or 1920

    def connect(self):
        """Detect and connect to the physical device."""
        print("Detecting connected devices...")
        connected = self.adb.check_connection()
        if connected:
            self.serial = self.adb.device_serial
            self.width = self.adb.width or 1080
            self.height = self.adb.height or 1920
            print(f"Connected to device: {self.serial}")
            print(f"Device Resolution: {self.width}x{self.height}")
            return True
        else:
            print("Error: No Android devices found via ADB.")
            return False

    def tap(self, x, y):
        """Simulate a tap at (x, y)."""
        self.adb.tap(x, y)

    def swipe(self, x1, y1, x2, y2, duration=300):
        """Simulate a swipe from (x1, y1) to (x2, y2)."""
        self.adb.swipe(x1, y1, x2, y2, duration_ms=duration)

    def scroll_down(self):
        """Hardcoded scroll down (swipe up)."""
        cx = self.width // 2
        start_y = int(self.height * 0.8)
        end_y = int(self.height * 0.2)
        self.swipe(cx, start_y, cx, end_y)

    def take_screenshot(self, save_path="tmp/screen.png"):
        """Capture screen and pull to local machine."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        cmd = self.adb.adb_cmd_prefix + ["shell", "screencap", "-p", "/sdcard/screen.png"]
        subprocess.run(cmd)
        cmd_pull = self.adb.adb_cmd_prefix + ["pull", "/sdcard/screen.png", save_path]
        subprocess.run(cmd_pull)
        return save_path

    def send_keyevent(self, keycode):
        """Send a hardware key event (e.g., 4 for Back)."""
        self.adb.keyevent(str(keycode))

if __name__ == "__main__":
    # Self-test
    ctrl = DeviceController()
    if ctrl.connect():
        print("Test: Taking screenshot...")
        ctrl.take_screenshot("tmp/test_conn.png")
        print("Success.")
