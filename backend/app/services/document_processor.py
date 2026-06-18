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
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text_content = page.extract_text()
                    if text_content:
                        text += text_content + "\n"
                return text.strip()
            except Exception as e:
                logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
                return ""
            
        elif file_extension in [".docx", ".doc"]:
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([p.text for p in doc.paragraphs]).strip()
            except Exception as e:
                logger.error(f"Error extracting text from Word document {file_path}: {str(e)}")
                return ""

        else:
            # Default text read attempt for other extensions
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""
