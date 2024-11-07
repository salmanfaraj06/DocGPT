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
    
# The run_flask() function starts the Flask server by running main.py.
# The run_streamlit() function starts the Streamlit app by running streamlit_app.py.
# The if __name__ == "__main__": block calls these functions in sequence.
# The time.sleep(5) line waits for 5 seconds before starting the Streamlit app to ensure the Flask server is up and running.
# This script will start the Flask server and Streamlit app in separate processes.

# Run the run_apps.py script in the terminal: python3 run_apps.py