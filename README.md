# 🧠 Smart Voice Assistant — Simba

**Simba** is a Python-based offline voice assistant designed for event management and general voice interaction. It supports real-time voice commands, wake-word detection, Google Sheets integration, and query logging into Word documents.


## 🔧 Features

- Wake word detection (Porcupine)
- Real-time voice input and output
- Google Sheets syncing for dynamic data
- LLM-based natural language processing
- Smart query confirmation (only for long/complete inputs)
- Optional voice history logging into `.docx` files


## 🚀 How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt

## Project Structure

smart-voice-assistant/
│
├── main.py                 # Main loop with wake word and query processing
├── llm_processor.py        # Handles LLM response and sheet syncing
├── history_logger.py       # Logs voice interactions into Word
├── sheets_helper.py        # To retrieve the google sheets
├── internal_memory.txt     # Text file which is used for providing rules,behaviour etc for your LLM
├── requirements.txt        # Python dependencies
├── user_history.docx       # (auto-created)
├── rag_memory/             # (auto-created)
├── credentials.json        # Google service account
├── README.md               # This file
├── LICENSE                 # MIT LICENSE

## Requirements:
Python 3.11+
Microphone and speaker
Internet connection (for LLM and Sheets)
Porcupine access key (hardcoded or passed)
16GB RAM with GPU for better performance

## Steps to implement this file:
1. Install python
2. Create a virtual environment
3. Pull the project folder
4. Install All Required Packages using  "pip install -r requirements.txt"
5. Install and Run Ollama (for LLM) (This project uses Llama3.2 as it is light weight and can run only on CPU)
6. Ensure Required Files Exist as per the project folder
7. For Credentials.json in this project, create a service account in Credentials from "https://console.developers.google.com/" and Enable a google sheets API
8. Download the credentials.json file and include the credentials.json file in your project directory.
9. Create a google sheet for your local assistant to retrieve, and link or share the created service account with any read or write mode.
10. For Wake word, Go to Picovoice Console, Get a free Access key. Include the access key in your project's Access key (because only one access key for one account).
11. Use default wake words or Custom wake words. if default, just include the wakeword name. if custom, include the wakeword name with "your wakeword.ppn" file
12. Provide an Internal memory (permanent background knowledge) for this project.
13. Run the file and work with your voice assistant.
