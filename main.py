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
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader

# Load environment variables from .env file
load_dotenv()

# Set environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = openai_api_key

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Initialize ChromaDB client and paths
chroma_client = chromadb.Client()
document_directory = "contents"  # Location of your PDFs
persist_directory = "chroma_persist"

def create_vector_db(doc_dir):
    try:
        logger.info(f"Starting vector database creation for {doc_dir}.")

        if os.path.isdir(doc_dir):
            loader = DirectoryLoader(doc_dir, glob="**/*.pdf", loader_cls=PyPDFLoader)
        elif doc_dir.endswith(".pdf"):
            loader = PyPDFLoader(doc_dir)
        else:
            raise ValueError("Provided path must be a directory of PDFs or a single PDF file.")

        documents = loader.load()
        logger.info(f"Loaded {len(documents)} documents.")

        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        texts = text_splitter.split_documents(documents)
        logger.info(f"Split documents into {len(texts)} chunks for embedding.")

        embeddings = OpenAIEmbeddings()
        vectordb = Chroma.from_documents(
            texts,
            embeddings,
            persist_directory=persist_directory,
            client=chroma_client,
            collection_name="customer_info"
        )

        logger.info("Vector database creation successful.")
        return vectordb

    except Exception as e:
        logger.error(f"Error in creating vector database: {e}")
        return None

vectordb = create_vector_db(document_directory)

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

@app.route("/query", methods=["POST"])
def query_documents():
    data = request.get_json()
    query = data.get("query")

    if not vectordb:
        logger.error("Vector database is not initialized.")
        return jsonify({"error": "Vector database is not initialized"}), 500

    try:
        logger.info(f"Processing query: {query}")

        qa = RetrievalQA.from_chain_type(
            llm=OpenAI(api_key=openai_api_key),
            chain_type="stuff",
            retriever=vectordb.as_retriever(search_kwargs={"k": 2}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        result = qa({"query": query})
        answer = result["result"]

        logger.info(f"Query answered successfully: {answer}")
        return jsonify({"answer": answer})

    except Exception as e:
        logger.error(f"Error in retrieving answer: {e}")
        return jsonify({"error": "Error processing the query"}), 500

if __name__ == "__main__":
    app.run()