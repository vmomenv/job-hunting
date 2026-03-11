import os
import json
import requests
import fitz  # PyMuPDF

class ResumeMatcher:
    def __init__(self, resume_path="data/resume.pdf", ollama_url="http://localhost:11434/api/generate"):
        self.resume_path = resume_path
        self.ollama_url = ollama_url
        self.resume_text = ""
        self.load_resume()

    def load_resume(self):
        """Extract text from the resume PDF."""
        if not os.path.exists(self.resume_path):
            print(f"Warning: Resume not found at {self.resume_path}. Please place your resume.pdf there.")
            return ""
        
        try:
            doc = fitz.open(self.resume_path)
            text = ""
            for page in doc:
                text += page.get_text()
            self.resume_text = text
            print(f"Successfully loaded resume: {len(text)} characters.")
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    def analyze_job(self, jd_text):
        """Send JD and Resume to LLM for comparison."""
        if not self.resume_text:
            return {"score": 0, "decision": "ignore", "error": "No resume loaded"}

        prompt = f"""
        任务：基于求职者的简历内容，分析以下岗位描述 (JD) 的匹配度。
        
        【求职者简历内容】：
        {self.resume_text[:2000]}  # 限制长度以防超出上下文
        
        【目标岗位描述】：
        {jd_text}
        
        请严格按以下 JSON 格式返回：
        {{
            "score": 匹配度分数 (0-100),
            "pros": ["理由1", "理由2", "理由3"],
            "cons": ["冲突点/劣势"],
            "decision": "apply" (建议申请) 或 "save" (待定) 或 "ignore" (跳过)
        }}
        """

        payload = {
            "model": "llama3",  # or "llama3-vision"
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            # Note: This requires Ollama running locally.
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = json.loads(response.json().get("response", "{}"))
                return result
            else:
                print(f"Ollama error: {response.status_code}")
                return self._fallback_match(jd_text)
        except Exception as e:
            print(f"Request error: {e}")
            return self._fallback_match(jd_text)

    def _fallback_match(self, jd_text):
        """Simple keyword-based fallback if LLM is unavailable."""
        keywords = ["python", "ai", "crawler", "agent", "自动化"]
        score = 0
        found = []
        for kw in keywords:
            if kw.lower() in jd_text.lower():
                score += 20
                found.append(kw)
        
        decision = "apply" if score >= 60 else ("save" if score >= 20 else "ignore")
        return {
            "score": score,
            "pros": [f"含有关键词: {f}" for f in found],
            "cons": ["LLM API 不可用，使用自动关键词匹配"],
            "decision": decision
        }

if __name__ == "__main__":
    # Test
    matcher = ResumeMatcher()
    result = matcher.analyze_job("招聘 Python 爬虫工程师，熟悉 ADB 和自动化脚本。")
    print(json.dumps(result, indent=4, ensure_ascii=False))
