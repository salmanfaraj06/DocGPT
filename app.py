# streamlit_app.py
import tracemalloc
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import requests
import os
import pickle
from typing import Optional, Dict
import time
from datetime import datetime
import pandas as pd
from config import CONFIG

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Document Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
        .stButton button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
        }
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        .chat-message {
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .chat-message.user {
            background-color: #d1e7dd;
            color: #0f5132;
        }
        .chat-message.assistant {
            background-color: #f8d7da;
            color: #842029;
        }
        .document-card {
            padding: 1rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
def init_session_state():
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'selected_files' not in st.session_state:
        st.session_state.selected_files = {}
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'service' not in st.session_state:
        st.session_state.service = None

# Authentication function with error handling
def authenticate_drive() -> Optional[object]:
    try:
        creds = None
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if os.path.exists("client_secret.json"):
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secret.json", 
                    ['https://www.googleapis.com/auth/drive.readonly']
                )
                creds = flow.run_local_server(port=8502)
                with open("token.pickle", "wb") as token:
                    pickle.dump(creds, token)
            else:
                st.error("client_secret.json not found. Please ensure it's in the correct directory.")
                return None
        
        service = build("drive", "v3", credentials=creds)
        st.session_state.authenticated = True
        return service
    
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None

# Enhanced file listing with search and filtering
def list_drive_items(service, parent_id: str = "root", query: str = "") -> list:
    try:
        # Base query for supported file types and folders
        mime_types = CONFIG["SUPPORTED_MIME_TYPES"].keys()
        mime_type_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
        
        # Combine with folder type and parent folder constraint
        base_query = f"(mimeType='application/vnd.google-apps.folder' or ({mime_type_query}))"
        folder_query = f"'{parent_id}' in parents and {base_query}"
        
        # Add name search if query provided
        if query:
            folder_query += f" and name contains '{query}'"
        
        results = service.files().list(
            q=folder_query,
            fields="files(id, name, mimeType, modifiedTime, size, parents)",
            orderBy="modifiedTime desc"
        ).execute()
        
        return results.get("files", [])
    except Exception as e:
        st.error(f"Error listing files: {str(e)}")
        return []

# File browser component
def file_browser():
    st.sidebar.title("📁 Document Browser")
    
    # Search box
    search_query = st.sidebar.text_input("🔍 Search files", "")
    
    # File type filter
    file_types = list(CONFIG["SUPPORTED_MIME_TYPES"].keys())
    selected_types = st.sidebar.multiselect(
        "Filter by type",
        file_types,
        default=file_types
    )
    
    # List files with search and filter
    items = list_drive_items(st.session_state.service, query=search_query)
    
    # Display files and folders in a scrollable container
    with st.sidebar.container():
        st.markdown("### Available Documents and Folders")
        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                # Display folder card
                with st.container():
                    col1, col2 = st.columns([8, 2])
                    
                    with col1:
                        icon = "📁"
                        title = f"{icon} {item['name']}"
                        is_selected = st.checkbox(
                            title,
                            key=f"folder_{item['id']}",
                            value=item['id'] in st.session_state.selected_files
                        )
                        
                        if is_selected and item['id'] not in st.session_state.selected_files:
                            st.session_state.selected_files[item['id']] = item
                        elif not is_selected and item['id'] in st.session_state.selected_files:
                            del st.session_state.selected_files[item['id']]
                    
                    with col2:
                        modified_date = datetime.fromisoformat(
                            item['modifiedTime'].replace('Z', '+00:00')
                        )
                        st.caption(modified_date.strftime('%Y-%m-%d'))
                
                # List contents of the selected folder
                if is_selected:
                    folder_items = list_drive_items(st.session_state.service, parent_id=item['id'])
                    for folder_item in folder_items:
                        if folder_item["mimeType"] in selected_types:
                            # Display file card
                            with st.container():
                                col1, col2 = st.columns([8, 2])
                                
                                with col1:
                                    icon = "📄"
                                    title = f"{icon} {folder_item['name']}"
                                    is_selected = st.checkbox(
                                        title,
                                        key=f"file_{folder_item['id']}",
                                        value=folder_item['id'] in st.session_state.selected_files
                                    )
                                    
                                    if is_selected and folder_item['id'] not in st.session_state.selected_files:
                                        st.session_state.selected_files[folder_item['id']] = folder_item
                                    elif not is_selected and folder_item['id'] in st.session_state.selected_files:
                                        del st.session_state.selected_files[folder_item['id']]
                                
                                with col2:
                                    modified_date = datetime.fromisoformat(
                                        folder_item['modifiedTime'].replace('Z', '+00:00')
                                    )
                                    st.caption(modified_date.strftime('%Y-%m-%d'))
            elif item["mimeType"] in selected_types:
                # Display file card
                with st.container():
                    col1, col2 = st.columns([8, 2])
                    
                    with col1:
                        icon = "📄"
                        title = f"{icon} {item['name']}"
                        is_selected = st.checkbox(
                            title,
                            key=f"file_{item['id']}",
                            value=item['id'] in st.session_state.selected_files
                        )
                        
                        if is_selected and item['id'] not in st.session_state.selected_files:
                            st.session_state.selected_files[item['id']] = item
                        elif not is_selected and item['id'] in st.session_state.selected_files:
                            del st.session_state.selected_files[item['id']]
                    
                    with col2:
                        modified_date = datetime.fromisoformat(
                            item['modifiedTime'].replace('Z', '+00:00')
                        )
                        st.caption(modified_date.strftime('%Y-%m-%d'))

# Chat interface component
def chat_interface():
    st.title("🤖 Smart Document Assistant")
    
    # Display selected documents
    if st.session_state.selected_files:
        st.write("### Selected Documents")
        for file_id, file_info in st.session_state.selected_files.items():
            st.info(f"📄 {file_info['name']}")
    
    # Chat input
    user_input = st.text_area("Ask a question about your documents:", height=100)
    
    # Submit button with loading state
    if st.button("Submit Question", disabled=not st.session_state.selected_files):
        if user_input:
            with st.spinner("Processing your question..."):
                try:
                    # Collect all selected file IDs
                    file_ids = list(st.session_state.selected_files.keys())
                    
                    # Send the request to the backend
                    response = requests.post(
                        "http://127.0.0.1:5000/query",
                        json={
                            "query": user_input,
                            "file_ids": file_ids
                        }
                    )
                    
                    if response.status_code == 200:
                        answer_data = response.json()
                        
                        # Add to chat history
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": user_input
                        })
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": answer_data["answer"],
                            "source_documents": answer_data.get("source_documents", [])
                        })
                    else:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                
                except Exception as e:
                    st.error(f"Error processing request: {str(e)}")
    
    # Display chat history
    st.write("### Conversation History")
    for message in st.session_state.chat_history:
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                    <div class="chat-message user">
                        <p><strong>You:</strong> {message['content']}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="chat-message assistant">
                        <p><strong>Assistant:</strong> {message['content']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Display source documents if available
                if "source_documents" in message:
                    with st.expander("View Source Documents"):
                        for idx, source in enumerate(message["source_documents"]):
                            st.markdown(f"**Source {idx + 1}:**")
                            st.markdown(source)

def main():
    init_session_state()
    
    # Authentication check
    if not st.session_state.authenticated:
        st.session_state.service = authenticate_drive()
        if not st.session_state.service:
            st.error("Please authenticate with Google Drive to continue.")
            return
    
    # Create two-column layout
    file_browser()
    chat_interface()

if __name__ == "__main__":
    main()