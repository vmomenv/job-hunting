import sys
import os
from src.controller import DeviceController
from src.vision import VisionEngine
from src.matcher import ResumeMatcher
from src.data_manager import DataManager

def main():
    print("🚀 Starting Job-Hunting Assistant...")
    
    # 1. Initialize Modules
    ctrl = DeviceController()
    vision = VisionEngine()
    matcher = ResumeMatcher()
    data_mgr = DataManager()

    # 2. Connect to Device
    if not ctrl.connect():
        print("❌ Failed to connect to device. Exiting.")
        return

    print("✅ System ready. Starting scan loop...")

    try:
        while True:
            # 3. Capture & Parse Screen
            print("\n📸 Capturing screen...")
            screen_path = ctrl.take_screenshot()
            elements = vision.parse_screen(screen_path)
            
            # 4. Find Job Cards
            jobs = vision.find_job_cards(elements)
            print(f"🔍 Found {len(jobs)} potential job cards.")

            for job in jobs:
                title = job["text"]
                print(f"📝 Analyzing: {title}")
                
                # Check for duplicates first
                if data_mgr.is_duplicate("Boss", title):  # Simplified company detection
                    print(f"⏩ {title} already processed. Skipping.")
                    continue

                # 5. Extract Detailed Info (Simulated for now)
                # In a real run, we would click the card, scrape the JD, then hit back.
                mock_jd = f"职位：{title}。要求：熟悉 Python 和自动化开发。"
                
                # 6. AI Match Analysis
                result = matcher.analyze_job(mock_jd)
                print(f"📊 Match Score: {result.get('score', 0)}")

                # 7. Save Result
                data_mgr.save_job(
                    platform="Boss",
                    company="AutoDetected",
                    title=title,
                    salary="Unknown",
                    score=result.get("score", 0),
                    decision=result.get("decision", "ignore"),
                    reasons=result.get("pros", [])
                )

                # 8. Decision-based Action
                if result.get("decision") == "apply":
                    print(f"✅ HIGH MATCH! Coordinates: {job['center']}")
                    # ctrl.tap(*job['center']) # Click into detail
                    # ... logic to apply ...

            # Infinite loop for now, or add exit condition
            print("\n😴 Sleeping for 10s before next scan...")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Stop requested. Goodbye!")

if __name__ == "__main__":
    main()
