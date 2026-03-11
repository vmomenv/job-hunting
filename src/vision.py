import os
import base64
import requests
import json

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

class VLMClient:
    def __init__(self, model="llama3-vision", api_url="http://localhost:11434/api/generate"):
        self.model = model
        self.api_url = api_url

    def query(self, image_path, prompt):
        """Send a query to the VLM with an image."""
        if not os.path.exists(image_path):
            return "Error: Image not found."

        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [encoded_image],
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            return f"Error: VLM request failed - {str(e)}"

class VisionEngine:
    def __init__(self, use_vlm=True, vlm_model="llama3-vision"):
        self.use_vlm = use_vlm
        self.vlm = VLMClient(model=vlm_model) if use_vlm else None
        self.ocr = None

    def _init_ocr(self):
        if not self.ocr and PaddleOCR:
            self.ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        return self.ocr

    def analyze_search_results(self, image_path, query_keyword="Python"):
        """Use VLM to find relevant jobs on the search results page."""
        prompt = f"""
        Identify job listings on this screen related to '{query_keyword}'.
        For each job card, provide:
        - Job Title
        - Company Name
        - Salary (e.g., 20k-30k)
        - Center Coordinates [x, y] for clicking the card.
        Return the result as a JSON array of objects.
        """
        if self.use_vlm:
            response_text = self.vlm.query(image_path, prompt)
            try:
                # Attempt to extract JSON from response
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                if start != -1 and end != -1:
                    return json.loads(response_text[start:end])
            except:
                print("Warning: Failed to parse VLM JSON response.")
        
        return []

    def get_job_detail_text(self, image_path):
        """Extract all job description text from a detail page."""
        if self.use_vlm:
            prompt = "Extract the complete job description (JD) and requirements from this screen."
            return self.vlm.query(image_path, prompt)
        
        # Fallback to OCR
        elements = self.parse_screen_ocr(image_path)
        return "\n".join([el["text"] for el in elements])

    def parse_screen_ocr(self, image_path):
        """Fallback OCR-based parsing."""
        ocr = self._init_ocr()
        if not ocr:
            return []

        result = ocr.ocr(image_path, cls=True)
        parsed_elements = []
        if result and result[0]:
            for line in result[0]:
                coords = line[0]
                text = line[1][0]
                cx = sum(p[0] for p in coords) / 4
                cy = sum(p[1] for p in coords) / 4
                parsed_elements.append({"text": text, "center": (int(cx), int(cy))})
        return parsed_elements

if __name__ == "__main__":
    # Test VLM capability if Ollama is running
    eng = VisionEngine()
    # Mock call
    print("VLM analysis (mock/requires local ollama):", eng.analyze_search_results("tmp/screen.png"))
