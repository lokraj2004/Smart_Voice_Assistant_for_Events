from langchain_ollama import OllamaLLM
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
import json
import os
from sheets_helper import fetch_event_data
from langchain_community.embeddings import HuggingFaceEmbeddings

# === Memory File Paths ===
INTERNAL_MEM_PATH = "internal_memory.txt"
PERMANENT_MEM_PATH = "Cerebral_cortex.txt"
VECTOR_STORE_DIR = "rag_memory"
TEMP_COMBINED_FILE = "temp_combined_memory.txt"

# === Initialize LLM and Embeddings ===
llm = OllamaLLM(model="llama3.2")
embedding = HuggingFaceEmbeddings(model_name="intfloat/e5-base")


def format_rows_with_headers(data):
    if not data or len(data) < 2:
        return "", ""

    title_block = "\n\n ### Pranav 2K25 — Event Details\n\n"

    headers = data[2]  # Assumes 3rd row has headers
    rows = data[3:]    # Event data from 4th row onward

    structured_json = []
    formatted_entries = []

    for idx, row in enumerate(rows, start=1):
        row += [""] * (len(headers) - len(row))  # Pad missing values
        event = dict(zip(headers, row))
        structured_json.append(event)

        # Create block format
        entry_lines = [
            f"🔹 Event {idx}\n"
        ]
        for header, value in event.items():
            entry_lines.append(f"- {header.strip()}: {value.strip()}")
        formatted_entries.append("\n".join(entry_lines))

    natural_text = title_block + "\n\n".join(formatted_entries)
    json_text = json.dumps(structured_json, indent=2)

    return natural_text, json_text


# === Fetch & Store Initial Internal Memory If Not Present ===
def initialize_internal_memory_once():
    if not os.path.exists(INTERNAL_MEM_PATH):
        print("[INFO] Loading internal memory from Google Sheets (initial load)...")
        data = fetch_event_data()
        if data:
            natural_text, _ = format_rows_with_headers(data)
            with open(INTERNAL_MEM_PATH, "w", encoding="utf-8") as f:
                f.write(natural_text)


# === Build Vectorstore from Both Memories ===
def build_vectorstore():
    combined_text = ""

    if os.path.exists(PERMANENT_MEM_PATH):
        with open(PERMANENT_MEM_PATH, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n"

    if os.path.exists(INTERNAL_MEM_PATH):
        with open(INTERNAL_MEM_PATH, "r", encoding="utf-8") as f:
            combined_text += f.read()

    with open(TEMP_COMBINED_FILE, "w", encoding="utf-8") as f:
        f.write(combined_text)

    loader = TextLoader(TEMP_COMBINED_FILE, encoding="utf-8")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(docs)

    return Chroma.from_documents(
        documents=split_docs,
        embedding=embedding,
        persist_directory=VECTOR_STORE_DIR
    )

# === Initialize memory and vectorstore ===
initialize_internal_memory_once()

if not os.path.exists(VECTOR_STORE_DIR):
    vectorstore = build_vectorstore()
else:
    vectorstore = Chroma(persist_directory=VECTOR_STORE_DIR, embedding_function=embedding)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 2})
)

# === Query Handler (no fetch_event_data here) ===
def handle_query_with_llm(query):
    return qa_chain.run(query)

# === Manual Sync to Refresh Internal Memory & Rebuild Vectorstore ===
def sync_google_sheet():
    try:
        print("[SYNC] Updating internal memory from Google Sheets...")
        data = fetch_event_data()
        if not data or len(data) < 2:
            print("[SYNC] No new data found.")
            return False

        natural_text, _ = format_rows_with_headers(data)
        with open(INTERNAL_MEM_PATH, "w", encoding="utf-8") as f:
            f.write(natural_text)

        global vectorstore, qa_chain
        vectorstore = build_vectorstore()

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 2})
        )

        print("[SYNC] Internal memory and vectorstore updated.")
        return True
    except Exception as e:
        print("[SYNC ERROR]", e)
        return False