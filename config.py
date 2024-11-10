# config.py
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "CHUNK_SIZE": 1000,
    "CHUNK_OVERLAP": 200,
    "PERSIST_DIRECTORY": "chroma_persist",
    "SUPPORTED_MIME_TYPES": {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    }
}