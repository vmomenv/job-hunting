import sys
import os

# Allow importing from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.controller import DeviceController
from src.vision import VisionEngine

def verify():
    print("🔍 Starting Verification...")
    
    # 1. Test ADB Connection
    ctrl = DeviceController()
    if ctrl.connect():
        print("✅ ADB Connection: SUCCESS")
        print(f"📱 Device: {ctrl.serial} ({ctrl.width}x{ctrl.height})")
    else:
        print("❌ ADB Connection: FAILED. Check if device is connected and USB debugging is on.")
        return

    # 2. Test VLM API (Ollama)
    vision = VisionEngine(use_vlm=True)
    print("📡 Testing VLM API (Ollama)...")
    
    # Take a temp screenshot for testing
    test_img = ctrl.take_screenshot("tmp/verify_vlm.png")
    
    # Simple query
    response = vision.vlm.query(test_img, "What is on the screen? Answer in one sentence.")
    if "Error" in response:
        print(f"❌ VLM API: FAILED - {response}")
        print("💡 Make sure Ollama is running and the model (llama3-vision) is pulled.")
    else:
        print(f"✅ VLM API: SUCCESS")
        print(f"🤖 VLM Response: {response}")

    print("\n✨ Verification Complete.")

if __name__ == "__main__":
    verify()
