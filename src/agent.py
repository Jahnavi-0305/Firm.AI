# src/agent.py
from typing import List, Dict, Optional
from groq import Groq
import json as pyjson
import regex as re

from .config import GROQ_API_KEY, GROQ_MODEL, MAX_RERANKED, TEMPERATURE
from .prompts import SYSTEM_GUARD, RERANK_INSTRUCTIONS, ANSWER_INSTRUCTIONS

client = Groq(api_key=GROQ_API_KEY)

def chat(messages, json_mode: bool = False):
    kwargs = {"temperature": TEMPERATURE}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return client.chat.completions.create(model=GROQ_MODEL, messages=messages, **kwargs)

def is_greeting_or_casual(question: str) -> bool:
    """Detect if the query is a greeting or casual chat"""
    q = question.lower().strip()
    greetings = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'bye', 'goodbye']
    return q in greetings or (any(q.startswith(g) for g in greetings) and len(q.split()) <= 5)

def handle_greeting(question: str) -> Dict:
    """Return a friendly greeting response"""
    return {
        "answer": "Hello! I'm your Legal RAG Assistant. Upload a PDF to analyze documents, or ask me about recent legal cases, GDPR enforcement, and regulations!",
        "citations": [],
        "used_chunks": 0
    }

def rerank_chunks(question: str, retrieved: List[Dict]) -> List[Dict]:
    """Rerank retrieved chunks by relevance"""
    if not retrieved:
        return []
    
    # Separate internal and external
    internal = [c for c in retrieved if c.get("source_type") != "external"]
    external = [c for c in retrieved if c.get("source_type") == "external"]
    
    print(f"📊 Reranking: {len(internal)} internal, {len(external)} external")
    
    # Build catalog for LLM reranking
    catalog = []
    for c in retrieved:
        if c.get("source_type") == "external":
            catalog.append({
                "id": c["id"],
                "type": "external",
                "source": c.get("url", "web"),
                "text": c.get("title", "") + ". " + c.get("snippet", "")[:300]
            })
        else:
            catalog.append({
                "id": c["id"],
                "type": "internal",
                "source": f"{c.get('doc_name', 'Doc')} p.{c.get('page_num', '?')}",
                "text": c["text"][:500]
            })
    
    # Let LLM select best chunks
    try:
        resp = chat(
            [
                {"role": "system", "content": SYSTEM_GUARD},
                {
                    "role": "user",
                    "content": f"Question: {question}\n{RERANK_INSTRUCTIONS}\n\n<CATALOG>\n{pyjson.dumps(catalog, indent=2, ensure_ascii=False)}\n</CATALOG>",
                },
            ],
            json_mode=True,
        )
        
        selection = pyjson.loads(resp.choices[0].message.content)
        chosen_ids = set(selection.get("chosen_ids", []))
        print(f"🎯 Rerank selected: {chosen_ids}")
        
    except Exception as e:
        print(f"⚠️ Rerank failed: {e}, using heuristic")
        # Fallback: Mix both sources
        chosen_ids = {c["id"] for c in (external[:3] + internal[:3])}
    
    selected = [c for c in retrieved if c["id"] in chosen_ids][:MAX_RERANKED]
    
    # Log final selection
    sel_int = len([c for c in selected if c.get("source_type") != "external"])
    sel_ext = len([c for c in selected if c.get("source_type") == "external"])
    print(f"✅ Final: {sel_int} internal, {sel_ext} external")
    
    return selected

def _context_block(selected: List[Dict]) -> str:
    """Format context with clear source attribution"""
    if not selected:
        return "No relevant information found."
    
    blocks = []
    internal_docs = [c for c in selected if c.get("source_type") != "external"]
    external_docs = [c for c in selected if c.get("source_type") == "external"]
    
    # Format internal documents
    if internal_docs:
        blocks.append("=== INTERNAL DOCUMENTS ===")
        for i, c in enumerate(internal_docs, 1):
            blocks.append(
                f"[INTERNAL-{i}] {c.get('doc_name', 'Document')} - Page {c.get('page_num', '?')}\n"
                f"{c['text']}\n"
            )
    
    # Format external web sources
    if external_docs:
        blocks.append("\n=== EXTERNAL WEB SOURCES ===")
        for i, c in enumerate(external_docs, 1):
            blocks.append(
                f"[EXTERNAL-{i}] {c.get('title', 'Web Source')}\n"
                f"URL: {c.get('url', 'N/A')}\n"
                f"{c.get('snippet', c.get('text', ''))}\n"
            )
    
    return "\n\n".join(blocks)

def answer(question: str, selected: List[Dict], history: Optional[List[Dict]] = None) -> Dict:
    """Generate answer with citation metadata"""
    
    # Handle greetings
    if is_greeting_or_casual(question):
        return handle_greeting(question)
    
    # Check if we have any context
    if not selected:
        return {
            "answer": "❌ I couldn't find relevant information for your question. Please try:\n- Uploading a PDF document\n- Rephrasing your question\n- Being more specific",
            "citations": [],
            "used_chunks": 0
        }
    
    # Count source types
    has_internal = any(c.get("source_type") != "external" for c in selected)
    has_external = any(c.get("source_type") == "external" for c in selected)
    
    print(f"💬 Answering with: internal={has_internal}, external={has_external}")
    
    # Build context
    context = _context_block(selected)
    hist = history or []
    
    # Build messages
    messages = [{"role": "system", "content": SYSTEM_GUARD}]
    messages.extend(hist)
    messages.append({
        "role": "user",
        "content": (
            f"{ANSWER_INSTRUCTIONS}\n\n"
            f"<CONTEXT>\n{context}\n</CONTEXT>\n\n"
            f"<QUESTION>\n{question}\n</QUESTION>"
        ),
    })

    # Get answer from LLM
    resp = chat(messages, json_mode=False)
    answer_text = resp.choices[0].message.content or ""
    
    # Build citations for UI
    citations = []
    for chunk in selected:
        if chunk.get("source_type") == "external":
            citations.append({
                "id": chunk["id"],
                "type": "external",
                "title": chunk.get("title", "External Source"),
                "url": chunk.get("url", ""),
                "preview": (chunk.get("snippet", "") or chunk.get("text", ""))[:150] + "..."
            })
        else:
            citations.append({
                "id": chunk["id"],
                "type": "internal",
                "doc_name": chunk.get("doc_name", "Unknown"),
                "page_num": chunk.get("page_num", 1),
                "preview": chunk["text"][:150] + "..."
            })
    
    return {
        "answer": answer_text,
        "citations": citations,
        "used_chunks": len(selected)
    }