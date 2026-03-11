import sys
import os
import time
import re
from src.controller import DeviceController
from src.vision import VisionEngine
from src.matcher import ResumeMatcher
from src.data_manager import DataManager

def main():
    print("🚀 Starting Job-Hunting Assistant (Vision-Guided)...")
    
    # 1. Initialize Modules
    ctrl = DeviceController()
    vision = VisionEngine(use_vlm=True) # Ensure VLM is enabled
    data_mgr = DataManager()
    
    # Matching thresholds from config
    min_salary_threshold = data_mgr.config.get("min_salary", 15)
    target_keyword = data_mgr.config.get("keywords", ["Python"])[0]

    # 2. Connect to Device
    if not ctrl.connect():
        print("❌ Failed to connect to device. Exiting.")
        return

    print(f"✅ System ready. Target: {target_keyword}, Min Salary: {min_salary_threshold}k")
    print("🔌 Please ensure your Android phone is on the job search results page.")

    try:
        while True:
            # 3. Capture & Analyze Search Results via VLM
            print("\n📸 Capturing search screen...")
            screen_path = ctrl.take_screenshot()
            
            # VLM returns structured job listings
            jobs = vision.analyze_search_results(screen_path, query_keyword=target_keyword)
            print(f"🔍 VLM found {len(jobs)} potential job cards.")

            for job in jobs:
                title = job.get("Job Title") or job.get("职位名称") or "Unknown"
                company = job.get("Company Name") or job.get("公司名称") or "Unknown"
                salary_str = job.get("Salary") or job.get("薪资") or "0k"
                coords = job.get("Center Coordinates") or job.get("坐标")

                print(f"📝 Checking: {title} at {company} ({salary_str})")
                
                # Check for duplicates
                if data_mgr.is_duplicate(company, title):
                    print(f"⏩ {company} - {title} already processed. Skipping.")
                    continue

                # Simple salary parsing logic
                try:
                    salary_match = re.search(r"(\d+)", salary_str)
                    salary_val = int(salary_match.group(1)) if salary_match else 0
                except:
                    salary_val = 0

                if salary_val < min_salary_threshold:
                    print(f"📉 Salary {salary_str} below threshold {min_salary_threshold}k. Skipping.")
                    continue

                # 4. Deep Dive if salary matches
                if coords and len(coords) == 2:
                    print(f"🎯 Clicking job card for {title} at {coords}...")
                    ctrl.tap(coords[0], coords[1])
                    time.sleep(2) # Wait for detail page to load

                    # Capture detail page
                    print("📸 Capturing job detail...")
                    detail_screen = ctrl.take_screenshot("tmp/detail.png")
                    jd_text = vision.get_job_detail_text(detail_screen)
                    
                    # 5. Save to Excel
                    data_mgr.save_job(
                        platform="Auto", 
                        company=company,
                        title=title,
                        salary=salary_str,
                        score=0, # Placeholder for further analysis
                        decision="potential",
                        reasons="Vision matched salary requirements"
                    )
                    
                    print(f"💾 Job saved to Excel for reference.")

                    # Go back to list
                    print("🔙 Returning to search results (Back key)...")
                    # Use standard Android back key
                    os.system(f"adb -s {ctrl.serial} shell input keyevent 4")
                    time.sleep(1.5)
                else:
                    print("⚠️ Missing coordinates for job card. skipping detail.")
                    # Still save the summary info if we can't click
                    data_mgr.save_job("Auto", company, title, salary_str, 0, "not_clicked", "Coordinates missing")

            # Scroll down for more results after processing current page
            print("\n📜 Scrolling down for more results...")
            ctrl.scroll_down()
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Stop requested. Goodbye!")

if __name__ == "__main__":
    main()
