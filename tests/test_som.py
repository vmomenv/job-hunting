import sys
import os
from PIL import Image

# Allow importing from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.vision import VisionEngine
from src.adb_utils import AdbController

def test_som():
    print("🧪 Testing Set-of-Marks (SoM) Annotation...")
    
    vision = VisionEngine()
    adb = AdbController()
    
    if not adb.check_connection():
        print("❌ ADB not connected. Please connect a device or emulator.")
        return

    print("📸 Taking screenshot and dumping UI XML...")
    screenshot = adb.get_screenshot()
    temp_path = "tmp/test_som_input.png"
    xml_path = "tmp/test_som_view.xml"
    if not os.path.exists("tmp"):
        os.makedirs("tmp")
    screenshot.save(temp_path)
    
    import subprocess
    subprocess.run([adb.adb_path, "-s", adb.device_serial, "shell", "uiautomator", "dump", "/sdcard/view_som.xml"], capture_output=True)
    subprocess.run([adb.adb_path, "-s", adb.device_serial, "pull", "/sdcard/view_som.xml", xml_path], capture_output=True)

    print("🎨 Annotating image using XML...")
    annotated_img, label_map = vision.get_annotated_screen(temp_path, xml_path=xml_path)
    
    if annotated_img:
        output_path = "tmp/test_som_output.png"
        annotated_img.save(output_path)
        print(f"✅ Annotated image saved to {output_path}")
        print(f"🔍 Found {len(label_map)} labeled elements.")
        for label, coords in list(label_map.items())[:5]:
            print(f"  - Label {label}: {coords}")
    else:
        print("❌ Annotation failed.")

if __name__ == "__main__":
    test_som()
