# PDF
import fitz             # PyMuPDF
from io import BytesIO  # Leer binarios

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    buffer = BytesIO(pdf_bytes)
    doc = fitz.open(stream=buffer, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text