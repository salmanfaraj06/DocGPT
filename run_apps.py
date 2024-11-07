import subprocess
import time

def run_flask():
    subprocess.Popen(["python3", "main.py"])

def run_streamlit():
    subprocess.Popen(["streamlit", "run", "streamlit_app.py"])

if __name__ == "__main__":
    run_flask()
    time.sleep(5) 
    run_streamlit()