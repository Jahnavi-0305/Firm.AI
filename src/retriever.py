# src/retriever.py
import chromadb
import requests
from sentence_transformers import SentenceTransformer
from typing import List, Dict
from src.config import STORAGE_DIR, TOP_K, YOU_API_KEY

class ChromaRetriever:
    def __init__(self):
        chroma_path = str(STORAGE_DIR / "chroma")
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection("legal_documents")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve(self, query: str, k: int = TOP_K):
        """Retrieve from internal ChromaDB with citation metadata"""
        emb = self.embedder.encode(query).tolist()
        results = self.collection.query(query_embeddings=[emb], n_results=k)
        docs = []
        
        if not results["ids"] or not results["ids"][0]:
            return docs
            
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            docs.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "section_path": metadata.get("section", "ROOT"),
                "page_num": metadata.get("page_num", 1),
                "doc_name": metadata.get("doc_name", "Unknown"),
                "source_type": "internal"
            })
        return docs


def you_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Search You.com API for external legal context
    Returns list of {title, url, snippet, source_type}
    """
    if not YOU_API_KEY:
        print("âš ï¸ YOU_API_KEY not set, skipping external search")
        return []
    
    try:
        headers = {"X-API-Key": YOU_API_KEY}
        params = {
            "query": query,
            "num_web_results": num_results
        }
        
        response = requests.get(
            "https://api.ydc-index.io/search",
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"âš ï¸ You.com API error: {response.status_code}")
            return []
        
        data = response.json()
        results = []
        
        for hit in data.get("hits", [])[:num_results]:
            results.append({
                "id": f"you_{len(results)}",
                "title": hit.get("title", ""),
                "url": hit.get("url", ""),
                "snippet": hit.get("description", ""),
                "source_type": "external",
                "text": f"{hit.get('title', '')}. {hit.get('description', '')}"
            })
        
        return results
        
    except Exception as e:
        print(f"âš ï¸ You.com search failed: {e}")
        return []


def hybrid_retrieve(query: str, retriever: ChromaRetriever, k_internal: int = 6, k_external: int = 4) -> List[Dict]:
    """
    CRITICAL HACKATHON FUNCTION: Performs hybrid retrieval
    Combines internal ChromaDB + external You.com results
    """
    # 1. Get internal documents with citation metadata
    internal_docs = retriever.retrieve(query, k_internal)
    
    # 2. Get external You.com results
    external_docs = you_search(query, k_external)
    
    # 3. Combine and return
    combined = internal_docs + external_docs
    
    print(f"ðŸ” Hybrid Retrieval: {len(internal_docs)} internal + {len(external_docs)} external = {len(combined)} total")
    
    return combined