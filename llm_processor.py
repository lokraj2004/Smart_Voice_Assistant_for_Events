from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

import os
from sheets_helper import fetch_event_data

# === Initialize LLM ===
llm = OllamaLLM(model="llama3.2")  # Ensure llama3.2 is pulled via Ollama

# === Memory file paths ===
INTERNAL_MEM_PATH = "internal_memory.txt"
PERMANENT_MEM_PATH = "Cerebral_cortex.txt"
VECTOR_STORE_DIR = "rag_memory"

embedding = OllamaEmbeddings(model="llama3.2")

# === Function to load and embed memory ===
def build_vectorstore():
    combined_text = ""

    # Load permanent memory
    if os.path.exists(PERMANENT_MEM_PATH):
        with open(PERMANENT_MEM_PATH, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n"

    # Load internal memory
    if os.path.exists(INTERNAL_MEM_PATH):
        with open(INTERNAL_MEM_PATH, "r", encoding="utf-8") as f:
            combined_text += f.read()

    # Save to a temp file for loading
    with open("temp_combined_memory.txt", "w", encoding="utf-8") as f:
        f.write(combined_text)

    loader = TextLoader("temp_combined_memory.txt", encoding="utf-8")
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(docs)

    return Chroma.from_documents(
        documents=split_docs,
        embedding=embedding,
        persist_directory=VECTOR_STORE_DIR
    )

# === Initialize vectorstore ===
if not os.path.exists(VECTOR_STORE_DIR):
    vectorstore = build_vectorstore()
else:
    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_DIR,
        embedding_function=embedding
    )

# === Setup QA chain ===
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
)

# === Query handler ===
def handle_query_with_llm(query):
    data = fetch_event_data()
    rows = data[1:]  # Skip header
    event_context = "\n".join([", ".join(row) for row in rows])

    full_prompt = f"""
You are an intelligent event assistant. Below are details of upcoming events:

{event_context}

Now, using your internal memory and event data, answer the following question:
{query}
"""

    return qa_chain.run(full_prompt)

# === Sync function for manual Google Sheet update ===
def sync_google_sheet():
    try:
        data = fetch_event_data()
        if not data or len(data) <= 1:
            return False

        # Format and refresh internal memory
        rows = data[1:]
        updated_context = "\n".join([", ".join(row) for row in rows])

        with open(INTERNAL_MEM_PATH, "w", encoding="utf-8") as f:
            f.write(updated_context)

        # Rebuild vectorstore with permanent + internal memory
        global vectorstore, qa_chain
        vectorstore = build_vectorstore()

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
        )

        return True
    except Exception as e:
        print("[Sync Error]", e)
        return False
