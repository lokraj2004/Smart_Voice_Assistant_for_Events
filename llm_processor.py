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

# === Load and embed internal memory ===
INTERNAL_MEM_PATH = "internal_memory.txt"
VECTOR_STORE_DIR = "rag_memory"

embedding = OllamaEmbeddings(model="llama3.2")

if not os.path.exists(VECTOR_STORE_DIR):
    # First-time setup: load and split memory, then embed
    loader = TextLoader(INTERNAL_MEM_PATH, encoding="utf-8")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    split_docs = splitter.split_documents(docs)

    vectorstore = Chroma.from_documents(
        documents=split_docs,
        embedding=embedding,
        persist_directory=VECTOR_STORE_DIR
    )
else:
    # Load existing embedded memory
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

        # Format and refresh memory with updated sheet content
        rows = data[1:]
        updated_context = "\n".join([", ".join(row) for row in rows])

        with open(INTERNAL_MEM_PATH, "w", encoding="utf-8") as f:
            f.write(updated_context)

        # Rebuild the vectorstore with new context
        loader = TextLoader(INTERNAL_MEM_PATH, encoding="utf-8")
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        split_docs = splitter.split_documents(docs)

        global vectorstore, qa_chain
        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=embedding,
            persist_directory=VECTOR_STORE_DIR
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
        )

        return True
    except Exception as e:
        print("[Sync Error]", e)
        return False
