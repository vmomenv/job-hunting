import subprocess
import os
import re
import time

class DeviceController:
    def __init__(self, serial=None):
        self.serial = serial
        self.width = 0
        self.height = 0

    def connect(self):
        """Detect and connect to the physical device."""
        print("Detecting connected devices...")
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")[1:]
        devices = [line.split("\t")[0] for line in lines if "\tdevice" in line]

        if not devices:
            print("Error: No Android devices found via ADB.")
            return False
        
        if self.serial and self.serial in devices:
            print(f"Using specified device: {self.serial}")
        else:
            self.serial = devices[0]
            print(f"Auto-selected device: {self.serial}")
        
        self.get_resolution()
        return True

    def get_resolution(self):
        """Query the device for its screen resolution."""
        result = subprocess.run(
            ["adb", "-s", self.serial, "shell", "wm", "size"], 
            capture_output=True, text=True
        )
        match = re.search(r"(\d+)x(\d+)", result.stdout)
        if match:
            self.width, self.height = int(match.group(1)), int(match.group(2))
            print(f"Device Resolution: {self.width}x{self.height}")
        else:
            print("Warning: Could not determine resolution. Defaulting to 1080x1920.")
            self.width, self.height = 1080, 1920

    def tap(self, x, y):
        """Simulate a tap at (x, y)."""
        subprocess.run(["adb", "-s", self.serial, "shell", "input", "tap", str(x), str(y)])

    def swipe(self, x1, y1, x2, y2, duration=300):
        """Simulate a swipe from (x1, y1) to (x2, y2)."""
        subprocess.run([
            "adb", "-s", self.serial, "shell", "input", "swipe", 
            str(x1), str(y1), str(x2), str(y2), str(duration)
        ])

    def scroll_down(self):
        """Hardcoded scroll down (swipe up)."""
        cx = self.width // 2
        start_y = int(self.height * 0.8)
        end_y = int(self.height * 0.2)
        self.swipe(cx, start_y, cx, end_y)

    def take_screenshot(self, save_path="tmp/screen.png"):
        """Capture screen and pull to local machine."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        subprocess.run(["adb", "-s", self.serial, "shell", "screencap", "-p", "/sdcard/screen.png"])
        subprocess.run(["adb", "-s", self.serial, "pull", "/sdcard/screen.png", save_path])
        return save_path

    def send_keyevent(self, keycode):
        """Send a hardware key event (e.g., 4 for Back)."""
        subprocess.run(["adb", "-s", self.serial, "shell", "input", "keyevent", str(keycode)])

if __name__ == "__main__":
    # Self-test
    ctrl = DeviceController()
    if ctrl.connect():
        print("Test: Taking screenshot...")
        ctrl.take_screenshot("tmp/test_conn.png")
        print("Success.")
