import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List

# --- RAG Libraries ---
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from langchain_community.embeddings import HuggingFaceEmbeddings

app = FastAPI(
    title="RAG Retriever API",
    version="1.0.0",
    description="Retrieval-Only API: Queries to vectorstore using LangChain, FAISS, and sentence-transformers.",
)


class RetrievalQueryInput(BaseModel):
    queries: List[str] = Field(
        ..., description="List of queries to retrieve from the vectorstore"
    )
    k: int = Field(3, description="Number of results per query", example=3)


class RetrievedDoc(BaseModel):
    query: str
    results: List[str]


class RetrievalResponse(BaseModel):
    responses: List[RetrievedDoc]


# --------- Initialize Retriever (on app startup) --------
VECTORSTORE_PATH = "faiss_index"  # Path to your FAISS vector store
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # Widely used, fast


def get_retriever():
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    try:
        vectorstore = FAISS.load_local(VECTORSTORE_PATH, embeddings=embedder, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever()
        return retriever
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Warning: Could not load FAISS index from {VECTORSTORE_PATH}: {e}")
        print("The /retrieve endpoint will not work until a FAISS index is created.")
        return None


retriever = get_retriever()
# --------------------------------------------------------


@app.post(
    "/retrieve",
    response_model=RetrievalResponse,
    summary="Retrieve top-k docs for each query",
)
def retrieve_docs(input: RetrievalQueryInput):
    """
    Given a list of user queries, returns top-k retrieved documents per query.
    """
    if retriever is None:
        raise HTTPException(
            status_code=503, 
            detail=f"FAISS index not available. Please ensure the index exists at {VECTORSTORE_PATH}"
        )
    
    try:
        out = []
        for q in input.queries:
            docs = retriever.get_relevant_documents(q, k=input.k)
            results = [doc.page_content for doc in docs]
            out.append(RetrievedDoc(query=q, results=results))
        return RetrievalResponse(responses=out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
