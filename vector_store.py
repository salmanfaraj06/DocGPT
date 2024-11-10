# vector_store.py
from typing import Optional, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document
import chromadb
from config import CONFIG
import logging

class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CONFIG["CHUNK_SIZE"],
            chunk_overlap=CONFIG["CHUNK_OVERLAP"],
            length_function=len
        )

    def create_vector_db(self, text: str, metadata: Optional[dict[str, Any]] = None) -> Optional[Chroma]:
        try:
            document = Document(page_content=text, metadata=metadata or {})
            texts = self.text_splitter.split_documents([document])
            
            return Chroma.from_documents(
                texts,
                self.embeddings,
                persist_directory=CONFIG["PERSIST_DIRECTORY"],
                client=self.client,
                collection_name=f"doc_{metadata.get('file_id', 'default')}"
            )
        except Exception as e:
            logging.error(f"Error creating vector database: {e}")
            return None