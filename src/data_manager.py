import os
import pandas as pd
from datetime import datetime
import yaml

class DataManager:
    def __init__(self, excel_path="data/jobs_table.xlsx", config_path="config.yaml"):
        self.excel_path = excel_path
        self.config_path = config_path
        self._init_excel()
        self.config = self.load_config()

    def _init_excel(self):
        """Create the Excel file if it doesn't exist."""
        if not os.path.exists(self.excel_path):
            os.makedirs(os.path.dirname(self.excel_path), exist_ok=True)
            df = pd.DataFrame(columns=[
                "Date", "Platform", "Company", "Title", "Salary", "Score", "Decision", "Reasons"
            ])
            df.to_excel(self.excel_path, index=False)
            print(f"Initialized data table: {self.excel_path}")

    def load_config(self):
        """Load settings from config.yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            # Default config
            default_cfg = {
                "min_score_apply": 80,
                "min_score_save": 50,
                "blacklisted_companies": []
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_cfg, f)
            return default_cfg

    def is_duplicate(self, company, title):
        """Check if the job has already been recorded."""
        df = pd.read_excel(self.excel_path)
        match = df[(df["Company"] == company) & (df["Title"] == title)]
        return not match.empty

    def save_job(self, platform, company, title, salary, score, decision, reasons):
        """Append a new job entry to the Excel file."""
        if self.is_duplicate(company, title):
            print(f"Skipping duplicate: {company} - {title}")
            return False

        new_entry = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Platform": platform,
            "Company": company,
            "Title": title,
            "Salary": salary,
            "Score": score,
            "Decision": decision,
            "Reasons": ", ".join(reasons) if isinstance(reasons, list) else reasons
        }

        df = pd.read_excel(self.excel_path)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_excel(self.excel_path, index=False)
        print(f"Saved: {company} - {title} (Score: {score})")
        return True

if __name__ == "__main__":
    # Test
    dm = DataManager()
    dm.save_job("Boss", "Tech Corp", "AI Engineer", "30k", 95, "apply", ["Experience matches", "Tech stack overlap"])
