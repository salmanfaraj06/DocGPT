import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import requests
import os
import pickle

# Scopes and credentials for Google Drive access
SCOPES = ['https://www.googleapis.com/auth/drive']


# Authenticate with Google Drive
def authenticate_drive():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
        creds = flow.run_local_server(port=8502)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("drive", "v3", credentials=creds)


# Function to list folders and files in Google Drive
def list_drive_items(service, parent_id="root"):
    results = service.files().list(q=f"'{parent_id}' in parents", fields="files(id, name, mimeType)").execute()
    items = results.get("files", [])
    return items


# Interface
st.title("Google Drive Document Selector")
service = authenticate_drive()


# Select Folder or File
def display_drive_folder(service, parent_id="root", indent=0):
    items = list_drive_items(service, parent_id)

    for item in items:
        if item["mimeType"] == "application/vnd.google-apps.folder":
            if st.checkbox(f"{' ' * indent}📁 {item['name']}", key=item["id"]):
                st.session_state.selected_folder_id = item["id"]
                display_drive_folder(service, item["id"], indent + 4)
        elif item["mimeType"] == "application/pdf":
            if st.checkbox(f"{' ' * indent}📄 {item['name']}", key=item["id"]):
                st.session_state.selected_file_id = item["id"]


st.write("Navigate Google Drive to select a PDF file or folder:")
display_drive_folder(service)

# Send selected file or folder to backend
if "selected_file_id" in st.session_state or "selected_folder_id" in st.session_state:
    query = st.text_input("Ask a question about the selected document or folder:")
    if st.button("Submit Query"):
        if query:
            file_id = st.session_state.get("selected_file_id") or st.session_state.get("selected_folder_id")
            response = requests.post("http://127.0.0.1:5000/query", json={
                "query": query,
                "file_id": file_id
            })
            if response.status_code == 200:
                st.write("Answer:", response.json().get("answer"))
            else:
                st.write("Error:", response.json().get("error"))
