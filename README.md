# Multimodal RAG Chatbot

An intelligent, full-stack Multimodal Retrieval-Augmented Generation (RAG) Chatbot. This application is capable of processing both text and documents (such as PDFs with images) to provide highly context-aware, insightful responses.

## 🌟 Key Features

* **Multimodal RAG**: Processes and understands complex queries involving both textual context and images parsed from documents.
* **Document Upload & Parsing**: Seamlessly drag-and-drop or upload PDF files. The backend extracts text, tables, and images using `pdfplumber` and `PyMuPDF`.
* **Dynamic Visual Responses**: The chatbot is capable of knowing when to return visual aids (images/figures) dynamically in the chat response based on user queries.
* **Intelligent Embeddings & Vector Search**: Utilizes Hugging Face `sentence-transformers` for creating embeddings and `Qdrant` as a robust vector database for rapid, semantic similarity search.
* **Advanced LLM Orchestration**: Integrated with LangChain to orchestrate leading Language Models (OpenAI, Groq/Llama-3, Hugging Face).
* **Secure Authentication & Tracking**: Built-in integration with Firebase Authentication to secure access, manage users, and track/limit query usage natively.
* **Modern Web Interface**: Clean, responsive frontend built with Next.js, React, and Lucide icons. Uses React Markdown structure to beautifully format LLM responses.

---

## 🏗️ Tech Stack

### Frontend
* **Framework**: [Next.js](https://nextjs.org/) (React 19)
* **Styling**: Vanilla CSS Modules (custom responsive design)
* **Icons & Rendering**: Lucide-React, React-Markdown, Remark-GFM
* **Auth**: Firebase Client SDK

### Backend
* **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
* **AI & Orchestration**: LangChain, Transformers, Torch
* **Vector Database**: Qdrant Vector Store
* **Auth & DB**: Firebase Admin SDK
* **File Processing**: PyMuPDF, pdfplumber, Pillow
* **Additional DB/Cache**: Redis

---

## 🚀 Getting Started Locally

### Prerequisites
* Node.js (v18+)
* Python 3.10+
* Docker (Optional, but recommended for Redis/Qdrant)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/MultliModal-RAG-Chatbot.git
cd MultliModal-RAG-Chatbot
```

### 2. Backend Setup
Navigate to the `backend` directory and set up a virtual environment:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

**Environment Variables:**
Create a `.env` file in the `backend/` directory referencing the required API keys:
```env
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
QDRANT_URL=your_qdrant_url
FIREBASE_PROJECT_ID=your_firebase_project_id
# Refer to the codebase for all expected keys
```
Make sure your `firebase-service-account.json` is correctly placed in the backend root.

**Start the FastAPI Server:**
```bash
python run.py 
# The server will run on http://localhost:8000
```

### 3. Frontend Setup
Navigate to the `frontend` directory:
```bash
cd ../frontend
npm install
```

**Environment Variables:**
Create a `.env.local` file in the `frontend/` directory with your Firebase config and API route:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=your_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_id
```

**Start the Next.js Development Server:**
```bash
npm run dev
# The frontend will run on http://localhost:3000
```

---

## 📄 License
This project is licensed under the MIT License. See the `LICENSE` file for details.
