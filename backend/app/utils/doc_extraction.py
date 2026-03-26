import fitz  # PyMuPDF
from docx import Document
import os
import base64
import io

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text from a PDF file using PyMuPDF."""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error extracting PDF text from {file_path}: {e}")
    return text

def pdf_to_base64_images(file_path: str) -> list[str]:
    """Converts each page of a PDF into a base64 encoded PNG image."""
    base64_images = []
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                # High-speed DPI (1.0 zoom) for multimodal sync
                pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                img_data = pix.tobytes("png")
                encoded = base64.b64encode(img_data).decode('utf-8')
                base64_images.append(encoded)
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
    return base64_images

def extract_text_from_docx(file_path: str) -> str:
    """Extracts text from a DOCX file using python-docx."""
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error extracting DOCX text from {file_path}: {e}")
    return text

def extract_text(file_path: str) -> str:
    """Extracts text based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        print(f"Unsupported file extension: {ext}")
        return ""
