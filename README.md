# DocGPT
This project is a chatbot application that leverages OpenAI's language model to answer questions based on the content of PDF documents. The application consists of a backend server built with Flask and a frontend interface using Streamlit. The backend processes queries by retrieving relevant information from a vector database created using ChromaDB and LangChain. The frontend allows users to input their questions and displays the answers retrieved from the backend.

# Key Features:
Backend: Flask server that handles queries and interacts with the vector database.
Frontend: Streamlit interface for user interaction.
Document Processing: Uses LangChain to split and embed text from PDF documents.
Vector Database: ChromaDB for storing and retrieving document embeddings.
Environment Configuration: Uses python-dotenv to manage environment variables.

# Technologies Used:
Python
Flask
Streamlit
ChromaDB
LangChain
OpenAI API
Requests
Python-dotenv

# Setup Instructions:
Install the required dependencies from requirements.txt.
Set up the .env file with your OpenAI API key.
Run the Flask server using python main.py.
Launch the Streamlit app using streamlit run streamlit_app.py.

# Files:
.env: Contains environment variables.
requirements.txt: Lists the project dependencies.
main.py: Backend server code.
streamlit_app.py: Frontend interface code.