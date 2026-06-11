import os
import logging

logger = logging.getLogger(__name__)

def extract_text_from_file(file_path: str) -> str:
    """
    Extract text content from an uploaded document file.
    Supports txt natively, and provides placeholders/imports for PDF/Docx.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return ""

    _, file_extension = os.path.splitext(file_path.lower())

    try:
        if file_extension == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
                
        elif file_extension == ".pdf":
            # In a full implementation, you'd use a library like pypdf or pdfplumber:
            # import pypdf
            # reader = pypdf.PdfReader(file_path)
            # text = ""
            # for page in reader.pages:
            #     text += page.extract_text() or ""
            # return text
            logger.info("PDF file detected. Using mock extraction for scaffolding.")
            return f"Mock PDF content extracted from {os.path.basename(file_path)}. In a real app, integrate a library like pypdf or pdfplumber."
            
        elif file_extension in [".docx", ".doc"]:
            # import docx
            # doc = docx.Document(file_path)
            # return "\n".join([p.text for p in doc.paragraphs])
            logger.info("Word document detected. Using mock extraction for scaffolding.")
            return f"Mock Word document content extracted from {os.path.basename(file_path)}."

        else:
            # Default text read attempt for other extensions
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""
