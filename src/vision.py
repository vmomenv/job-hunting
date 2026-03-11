import os
import base64
import requests
import json
import xml.etree.ElementTree as ET
import re
from PIL import Image, ImageDraw, ImageFont

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

        result = ocr.ocr(str(image_path), cls=True)
        parsed_elements = []
        if result and result[0]:
            for line in result[0]:
                coords = line[0]
                text = line[1][0]
                cx = sum(p[0] for p in coords) / 4
                cy = sum(p[1] for p in coords) / 4
                parsed_elements.append({
                    "text": text,
                    "center": (int(cx), int(cy)),
                    "bbox": [int(coords[0][0]), int(coords[0][1]), int(coords[2][0]), int(coords[2][1])]
                })
        return parsed_elements

    def parse_screen_uiautomator(self, xml_path):
        """Parse UI Automator XML to find clickable and interactive elements."""
        if not os.path.exists(xml_path):
            return []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception as e:
            print(f"Error parsing UI XML: {e}")
            return []

        elements = []
        # Find all nodes with bounds
        for node in root.iter():
            bounds = node.get("bounds")
            if not bounds:
                continue

            # Check if interactive
            is_clickable = node.get("clickable") == "true"
            is_enabled = node.get("enabled") == "true"
            text = node.get("text")
            content_desc = node.get("content-desc")
            
            # We want elements that are clickable OR have meaningful text
            if (is_clickable and is_enabled) or (text and len(text) > 0) or (content_desc and len(content_desc) > 0):
                # Parse bounds [x1,y1][x2,y2]
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    # Skip very small elements or full screen elements
                    if (x2 - x1) < 10 or (y2 - y1) < 10:
                        continue
                    
                    elements.append({
                        "text": text or content_desc or "",
                        "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                        "bbox": [x1, y1, x2, y2]
                    })
        
        # Deduplicate overlapping elements
        unique_elements = []
        for el in elements:
            is_dup = False
            for uel in unique_elements:
                if abs(el["center"][0] - uel["center"][0]) < 20 and abs(el["center"][1] - uel["center"][1]) < 20:
                    is_dup = True
                    break
            if not is_dup:
                unique_elements.append(el)

        return unique_elements

    def get_annotated_screen(self, image_path, xml_path=None):
        """
        Produce an annotated version of the screenshot with numeric labels.
        Returns (annotated_pil_image, label_map)
        """
        if not os.path.exists(image_path):
            return None, {}

        # 1. Parse elements: prefer XML, fallback to OCR
        elements = []
        if xml_path and os.path.exists(xml_path):
            elements = self.parse_screen_uiautomator(xml_path)
        
        if not elements:
            elements = self.parse_screen_ocr(image_path)
        
        # 2. Draw annotations
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        label_map = {}
        for i, el in enumerate(elements):
            label_id = str(i + 1)
            bbox = el["bbox"]
            center = el["center"]
            
            # Draw bbox
            draw.rectangle(bbox, outline="red", width=2)
            
            # Draw label background
            label_text = f" {label_id} "
            try:
                # Try to load a font, fallback to default
                font = ImageFont.truetype("arial.ttf", 18)
            except:
                font = ImageFont.load_default()
            
            # Use textbbox if available (Pillow 10.0+) or fallback
            if hasattr(draw, "textbbox"):
                t_bbox = draw.textbbox((bbox[0], bbox[1]), label_text, font=font)
            else:
                # Older Pillow versions
                tw, th = draw.textsize(label_text, font=font)
                t_bbox = (bbox[0], bbox[1], bbox[0] + tw, bbox[1] + th)
            
            draw.rectangle(t_bbox, fill="red")
            draw.text((bbox[0], bbox[1]), label_text, fill="white", font=font)
            
            label_map[label_id] = center

        return image, label_map

if __name__ == "__main__":
    # Test VLM capability if Ollama is running
    eng = VisionEngine()
    # Mock call
    print("VLM analysis (mock/requires local ollama):", eng.analyze_search_results("tmp/screen.png"))
