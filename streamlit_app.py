import requests
import streamlit as st

st.title("Emojot Chatbot")

query = st.text_input("Ask a question about your documents:")

if st.button("Submit"):
    if query:
        response = requests.post("http://127.0.0.1:5000/query", json={"query": query})
        if response.status_code == 200:
            answer = response.json().get("answer")
            st.write("Answer:", answer)
        else:
            st.write("Error:", response.json().get("error"))
    else:
        st.write("Please enter a question.")
