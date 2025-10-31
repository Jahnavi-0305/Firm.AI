# Firm.AI

Installation & Setup
Clone the Repository

Bash

git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Create a Virtual Environment

Bash

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies Create a requirements.txt file with the following content and run pip install -r requirements.txt:

Plaintext

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
Set Up Environment Variables Create a .env file in the project root and add your API keys:

Code snippet

# .env
GROQ_API_KEY=sk-your-groq-api-key
YOU_API_KEY=your-you-com-api-key
Run the Application The Flask server will start, automatically creating the necessary storage and uploads directories.

Bash

python server.py
You can now access the assistant at http://localhost:8000.

🔌 API Endpoints
GET /: Serves the main legal_rag.html frontend.

POST /upload: Handles PDF file uploads. It processes, chunks, and indexes the document, making it ready for querying.

POST /chat: Receives a user's question and (optionally) chat history. Performs the full RAG pipeline (retrieve, rerank, generate) and returns a JSON response with the answer and citations.

GET /health: A simple health check endpoint.

GET /pdf/<filename>: Serves the uploaded PDF file to the frontend's pdf.js viewer.
