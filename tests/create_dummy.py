from reportlab.pdfgen import canvas
import os

def create_dummy_resume(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path)
    c.drawString(100, 750, "Resume: John Doe")
    c.drawString(100, 730, "Skills: Python, Java, SQL, Machine Learning, Docker, Kubernetes")
    c.drawString(100, 710, "Experience: Senior Software Engineer at Tech Corp")
    c.save()
    print(f"Created dummy resume at {path}")

if __name__ == "__main__":
    create_dummy_resume("data/resume.pdf")
