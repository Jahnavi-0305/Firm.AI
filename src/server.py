import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os
import orjson as json
from pathlib import Path
from PyPDF2 import PdfReader
import uuid
import regex as re
import chromadb
from sentence_transformers import SentenceTransformer

from src.agent import rerank_chunks, answer
from src.retriever import ChromaRetriever, hybrid_retrieve
from src.config import TOP_K, STORAGE_DIR, UPLOADS_DIR, CHUNKS_PATH, CHROMA_PATH

app = Flask(__name__, template_folder="../templates")

ALLOWED_EXTENSIONS = {'pdf'}
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Global state
retriever = None
current_document = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()

def process_pdf(filepath):
    """Extract text from PDF with page-level metadata"""
    doc_name = Path(filepath).stem
    
    try:
        reader = PdfReader(filepath)
        chunks = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if not page_text.strip():
                continue
            
            # Split page into smaller chunks
            words = page_text.split()
            chunk_size = 800
            overlap = 150
            
            for i in range(0, len(words), chunk_size - overlap):
                chunk_text = " ".join(words[i:i + chunk_size])
                if not chunk_text.strip():
                    continue
                
                chunks.append({
                    "id": str(uuid.uuid4())[:8],
                    "doc_name": doc_name,
                    "page_num": page_num,
                    "text": normalize(chunk_text),
                    "section_path": f"{doc_name} - Page {page_num}"
                })
        
        return chunks
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return []

def rebuild_index(chunks):
    """Rebuild ChromaDB index with new chunks"""
    chroma_path = str(CHROMA_PATH)
    client = chromadb.PersistentClient(path=chroma_path)
    
    # Delete old collection
    try:
        client.delete_collection("legal_documents")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection("legal_documents")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    print(f"📚 Indexing {len(chunks)} chunks...")
    
    for c in chunks:
        emb = embedder.encode(c["text"]).tolist()
        collection.add(
            ids=[c["id"]],
            embeddings=[emb],
            documents=[c["text"]],
            metadatas=[{
                "section": c.get("section_path", "ROOT"),
                "page_num": c.get("page_num", 1),
                "doc_name": c.get("doc_name", "Unknown")
            }]
        )
    
    print(f"✅ Index built with {len(chunks)} chunks")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True, 
        "current_doc": current_document,
        "has_retriever": retriever is not None
    })

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle PDF upload and process it dynamically"""
    global current_document, retriever
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files allowed"}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = UPLOADS_DIR / filename
        file.save(str(filepath))
        
        print(f"📄 Processing: {filename}")
        
        chunks = process_pdf(str(filepath))
        
        if not chunks:
            return jsonify({"error": "Failed to extract text from PDF"}), 500
        
        STORAGE_DIR.mkdir(exist_ok=True)
        with open(CHUNKS_PATH, "wb") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk) + b"\n")
        
        print(f"💾 Saved {len(chunks)} chunks")
        
        rebuild_index(chunks)
        retriever = ChromaRetriever()
        
        num_pages = max([c.get("page_num", 1) for c in chunks])
        
        current_document = {
            "filename": filename,
            "path": str(filepath),
            "num_chunks": len(chunks),
            "pages": num_pages
        }
        
        return jsonify({
            "success": True,
            "document": current_document,
            "message": f"✅ Processed {len(chunks)} chunks from {filename} ({num_pages} pages)"
        })
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/pdf/<filename>")
def serve_pdf(filename):
    """Serve uploaded PDF for viewing in UI"""
    return send_from_directory(str(UPLOADS_DIR), filename)

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    """Handle chat queries with HYBRID support (doc + web)"""
    global retriever, current_document
    
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    history = data.get("history", [])

    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        # CRITICAL FIX: Initialize empty retriever if none exists
        if not retriever:
            print("⚠️ No document uploaded, initializing empty retriever")
            retriever = ChromaRetriever()
        
        print(f"\n🔍 Query: {question}")
        
        # HYBRID RETRIEVAL: Always get both internal + external
        retrieved = hybrid_retrieve(question, retriever, k_internal=6, k_external=4)
        
        print(f"📊 Retrieved {len(retrieved)} total chunks")
        
        # Rerank chunks
        selected = rerank_chunks(question, retrieved)
        
        print(f"✅ Selected {len(selected)} chunks for answer")
        
        # Generate answer with citations
        result = answer(question, selected, history=history)
        
        # Add current document info if available
        if current_document:
            result["current_document"] = current_document
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return render_template("legal_rag.html")

if __name__ == "__main__":
    print("🚀 Legal RAG Assistant Starting...")
    print("📂 Upload folder:", UPLOADS_DIR)
    print("💾 Storage folder:", STORAGE_DIR)
    print("🌐 Open: http://localhost:8000")
    
    # Initialize empty retriever on startup
    try:
        retriever = ChromaRetriever()
        print("✅ Retriever initialized")
    except Exception as e:
        print(f"⚠️ Retriever will initialize on first query: {e}")
    
    app.run(host="0.0.0.0", port=8000, debug=True)