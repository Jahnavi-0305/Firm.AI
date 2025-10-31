# Legal RAG Assistant 

This project is an advanced Retrieval-Augmented Generation (RAG) agent designed specifically for analyzing dense legal documents. It provides a web-based chat interface where users can upload a PDF (like a contract, regulation, or NDA) and ask complex questions.

Its core feature is a **Hybrid Retrieval** and **LLM Reranking** pipeline, which combines semantic search of the user's document with real-time web results to provide comprehensive, accurate, and fully-cited answers.

### ✨ Key Features

  * **Dynamic PDF Processing:** Upload and index legal documents on the fly.
  * **Hybrid Search:** Queries are run against *both* the internal document (using **ChromaDB**) and the external web (using the **You.com API**) to gather a complete set of facts.
  * **LLM Reranking:** A **Groq Llama 3.3** model intelligently reranks the combined search results to select only the most relevant chunks, filtering out noise *before* the final answer is generated.
  * **Blazing-Fast Generation:** Uses the **Groq API** for near-instantaneous answer generation and reranking.
  * **Interactive UI:** A two-panel interface built with JavaScript and `pdf.js` allows users to view the uploaded document and chat with the assistant simultaneously.
  * **Built-in Citations:** The frontend is designed to parse citations and includes (mocked) functionality to highlight the source text directly in the PDF viewer.

-----

### Tech Stack

  * **Backend:** **Flask** (serving the API and frontend)
  * **Frontend:** Plain **HTML**, **JavaScript**, and **TailwindCSS** (via CDN)
  * **PDF Rendering:** **`pdf.js`**
  * **LLM (Generation & Reranking):** **Groq** (using `llama-3.3-70b-versatile`)
  * **Vector Database:** **ChromaDB** (persistent)
  * **Embedding Model:** **SentenceTransformers** (`all-MiniLM-L6-v2`)
  * **External Search:** **You.com API**
  * **PDF Parsing:** **PyPDF2**

-----

### Architecture & Data Flow

1.  **Upload:** A user uploads a PDF via the UI.
2.  **Ingestion (`POST /upload`):**
      * The Flask server saves the file.
      * `PyPDF2` extracts text page by page.
      * The text is split into \~800-word chunks.
      * The `SentenceTransformer` model embeds each chunk.
      * The chunks, metadata (page number, doc name), and embeddings are stored in `ChromaDB`.
3.  **Chat (`POST /chat`):**
      * A user asks a question (e.g., "What is the notice period for termination?").
      * **Hybrid Retrieval:** The system retrieves the `TOP_K` most relevant chunks from `ChromaDB` AND fetches 4-6 external web results from the `You.com API`.
      * **LLM Reranking:** All retrieved chunks (internal + external) are sent to the Groq LLM. The LLM is tasked to *select* only the `MAX_RERANKED` (e.g., 6) chunks that are *most relevant* to the question.
      * **Generation:** The final, curated set of 6 chunks is passed to the Groq LLM with a prompt to synthesize an answer and cite its sources.
      * **Response:** The final answer and structured citation data are sent back to the frontend.

-----

### Installation & Setup

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create a Virtual Environment**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    Create a `requirements.txt` file with the following content and run `pip install -r requirements.txt`:

    ```txt
    # requirements.txt
    flask
    werkzeug
    orjson
    PyPDF2
    chromadb
    sentence-transformers
    regex
    requests
    groq
    python-dotenv
    ```

4.  **Set Up Environment Variables**
    Create a `.env` file in the project root and add your API keys:

    ```.env
    # .env
    GROQ_API_KEY=sk-your-groq-api-key
    YOU_API_KEY=your-you-com-api-key
    ```

5.  **Run the Application**
    The Flask server will start, automatically creating the necessary `storage` and `uploads` directories.

    ```bash
    python server.py
    ```

    You can now access the assistant at `http://localhost:8000`.

-----

### API Endpoints

  * `GET /`: Serves the main `legal_rag.html` frontend.
  * `POST /upload`: Handles PDF file uploads. It processes, chunks, and indexes the document, making it ready for querying.
  * `POST /chat`: Receives a user's question and (optionally) chat history. Performs the full RAG pipeline (retrieve, rerank, generate) and returns a JSON response with the answer and citations.
  * `GET /health`: A simple health check endpoint.
  * `GET /pdf/<filename>`: Serves the uploaded PDF file to the frontend's `pdf.js` viewer.
