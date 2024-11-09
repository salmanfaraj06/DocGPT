import os
import chromadb
import logging
from flask import Flask, request, jsonify
from langchain_openai import OpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
import fitz
from langchain.docstore.document import Document
import io
from googleapiclient.http import MediaIoBaseDownload

from streamlit_app import authenticate_drive

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = openai_api_key

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

chroma_client = chromadb.Client()
persist_directory = "chroma_persist"


# Function to download and extract text from PDF files
def download_pdf_text(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return extract_text_from_pdf(fh)


def extract_text_from_pdf(file_obj):
    text = ""
    with fitz.open(stream=file_obj, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text


# Function to create vector database
def create_vector_db(service, file_id):
    if not file_id:
        logger.error("Missing required parameter 'fileId'")
        return None

    try:
        pdf_text = download_pdf_text(service, file_id)
        document = Document(page_content=pdf_text)
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.split_documents([document])

        embeddings = OpenAIEmbeddings()
        vectordb = Chroma.from_documents(
            texts,
            embeddings,
            persist_directory=persist_directory,
            client=chroma_client,
            collection_name="customer_info"
        )
        return vectordb

    except Exception as e:
        logger.error(f"Error creating vector database: {e}")
        return None


# Template for prompt
template = """
You are an expert assistant with extensive knowledge in various domains. Use the provided context to answer the question accurately and concisely. If the answer is not in the context, state that you don't know.

Context:
{context}

Instructions:
- Provide a detailed and accurate answer based on the context.
- If the context does not contain the answer, respond with "I don't know."
- Do not make up any information.

Question:
{question}
"""
PROMPT = PromptTemplate(template=template, input_variables=["context", "question"])


# Query route
@app.route("/query", methods=["POST"])
def query_documents():
    data = request.get_json()
    query = data.get("query")
    file_id = data.get("file_id")
    service = authenticate_drive()  # Ensure service is authenticated

    # Pass file_id to the vector database function
    vectordb = create_vector_db(service, file_id)

    if vectordb is None:
        return jsonify({"error": "Failed to create vector database"}), 500

    try:
        qa = RetrievalQA.from_chain_type(
            llm=OpenAI(api_key=openai_api_key),
            chain_type="stuff",
            retriever=vectordb.as_retriever(search_kwargs={"k": 2}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        result = qa({"query": query})
        return jsonify({"answer": result["result"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
