# main.py
from flask import Flask, request, jsonify
from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from googleapiclient.http import MediaIoBaseDownload
import io
import logging
from typing import Optional, Tuple, List
from config import CONFIG
from document_processor import DocumentFactory
from vector_store import VectorStore
from app import authenticate_drive, list_drive_items
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import fitz

app = Flask(__name__)
vector_store = VectorStore()
openai_api_key = CONFIG["OPENAI_API_KEY"]

def download_file(service, file_id: str) -> Optional[str]:
    try:
        file_metadata = service.files().get(fileId=file_id, fields='mimeType').execute()
        mime_type = file_metadata['mimeType']
        
        if mime_type == "application/vnd.google-apps.folder":
            return None  # Skip folders

        if mime_type not in CONFIG["SUPPORTED_MIME_TYPES"]:
            raise ValueError(f"Unsupported file type: {mime_type}")

        request = service.files().get_media(fileId=file_id)
        file_obj = io.BytesIO()
        downloader = MediaIoBaseDownload(file_obj, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        file_obj.seek(0)
        
        processor = DocumentFactory.get_processor(mime_type)
        if processor:
            return processor.extract_text(file_obj)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        return None

def download_folder_contents(service, folder_id: str) -> List[str]:
    try:
        items = list_drive_items(service, parent_id=folder_id)
        file_texts = []
        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                file_texts.extend(download_folder_contents(service, item["id"]))
            else:
                file_text = download_file(service, item["id"])
                if file_text:
                    file_texts.append(file_text)
        return file_texts
    except Exception as e:
        logging.error(f"Error downloading folder contents: {e}")
        return []

PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are an expert assistant with extensive knowledge in various domains. Use the provided context to answer the question accurately and concisely.

Context:
{context}

Question: {question}

Instructions:
- Provide a detailed and accurate answer based on the context
- If the information isn't in the context, state "I don't have enough information to answer this question"
- Include relevant quotes or references from the document when applicable
- Be clear and concise in your response

Answer:
"""
)

@app.route("/query", methods=["POST"])
def query_documents():
    data = request.get_json()
    logging.info(f"Received request data: {data}")

    query = data.get("query")
    file_ids = data.get("file_ids")

    if not query or not file_ids:
        logging.error("Missing 'query' or 'file_ids' in request")
        return jsonify({"error": "Missing 'query' or 'file_ids' in request"}), 400

    service = authenticate_drive()  # Ensure service is authenticated

    documents = []
    for file_id in file_ids:
        file_metadata = service.files().get(fileId=file_id, fields='mimeType').execute()
        mime_type = file_metadata['mimeType']
        if mime_type == "application/vnd.google-apps.folder":
            folder_texts = download_folder_contents(service, file_id)
            for text in folder_texts:
                documents.append(Document(page_content=text))
        else:
            file_text = download_file(service, file_id)
            if file_text is None:
                logging.error(f"Failed to download file with ID {file_id}")
                return jsonify({"error": f"Failed to download file with ID {file_id}"}), 500
            documents.append(Document(page_content=file_text))

    if not documents:
        logging.error("No valid documents found")
        return jsonify({"error": "No valid documents found"}), 400

    try:
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.split_documents(documents)

        embeddings = OpenAIEmbeddings()
        vectordb = Chroma.from_documents(
            texts,
            embeddings,
            persist_directory=CONFIG["PERSIST_DIRECTORY"],
            client=vector_store.client,
            collection_name="customer_info"
        )

        qa = RetrievalQA.from_chain_type(
            llm=OpenAI(api_key=openai_api_key),
            chain_type="stuff",
            retriever=vectordb.as_retriever(search_kwargs={"k": 2}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT_TEMPLATE}
        )
        result = qa.invoke({"query": query})  # Use invoke method to avoid deprecation warning
        return jsonify({"answer": result["result"]})

    except Exception as e:
        logging.error(f"Error creating vector database: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/process", methods=["POST"])
def process_file():
    data = request.get_json()
    file_id = data.get("file_id")
    mime_type = data.get("mime_type")
    service = authenticate_drive()  # Ensure service is authenticated

    try:
        file_text = download_file(service, file_id)
        if file_text is None:
            return jsonify({"error": "Failed to download file"}), 500

        document = Document(page_content=file_text)
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.split_documents([document])

        embeddings = OpenAIEmbeddings()
        vectordb = Chroma.from_documents(
            texts,
            embeddings,
            persist_directory=CONFIG["PERSIST_DIRECTORY"],
            client=vector_store.client,
            collection_name="customer_info"
        )
        return jsonify({"message": "File processed successfully"})

    except Exception as e:
        logging.error(f"Error processing file {file_id}: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False)