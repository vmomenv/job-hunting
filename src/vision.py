import os
try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

class VisionEngine:
    def __init__(self, lang="ch"):
        self.lang = lang
        self.ocr = None
        if PaddleOCR:
            # We initialize OCR lazily to save resources if not needed
            pass

    def _init_ocr(self):
        if not self.ocr and PaddleOCR:
            self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
        return self.ocr

    def parse_screen(self, image_path):
        """Run OCR on the entire screenshot and return structured data."""
        if not os.path.exists(image_path):
            print(f"Error: Screenshot not found at {image_path}")
            return []

        ocr = self._init_ocr()
        if not ocr:
            print("Warning: PaddleOCR not installed. Returning mock data.")
            return self._get_mock_data()

        result = ocr.ocr(image_path, cls=True)
        
        parsed_elements = []
        if result and result[0]:
            for line in result[0]:
                coords = line[0]  # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                text = line[1][0]
                confidence = line[1][1]
                
                # Calculate center
                cx = sum(p[0] for p in coords) / 4
                cy = sum(p[1] for p in coords) / 4
                
                parsed_elements.append({
                    "text": text,
                    "center": (int(cx), int(cy)),
                    "box": coords,
                    "confidence": confidence
                })
        
        return parsed_elements

    def find_button_by_text(self, elements, target_text):
        """Look for a specific text in parsed elements and return its center."""
        for el in elements:
            if target_text in el["text"]:
                return el["center"]
        return None

    def find_job_cards(self, elements):
        """
        Heuristic: Job cards usually contain salary info (e.g., '15-25k').
        In a real app, we might look for specific UI patterns.
        """
        job_cards = []
        for el in elements:
            # Simple regex search for salary patterns could be added here
            if "K" in el["text"].upper() or "薪" in el["text"]:
                job_cards.append(el)
        return job_cards

    def _get_mock_data(self):
        """Mock data for testing when OCR is unavailable."""
        return [
            {"text": "Python开发", "center": (360, 400), "confidence": 0.99},
            {"text": "20K-40K", "center": (600, 400), "confidence": 0.99},
            {"text": "立即沟通", "center": (600, 1100), "confidence": 0.99}
        ]

if __name__ == "__main__":
    # Test
    eng = VisionEngine()
    # Assuming a sample image exists or using mock
    elements = eng.parse_screen("tmp/screen.png")
    for el in elements:
        print(f"Found: {el['text']} at {el['center']}")
