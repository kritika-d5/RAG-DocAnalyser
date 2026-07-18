# DocAnalyser — RAG-based Document Q&A

A Retrieval-Augmented Generation (RAG) system for asking natural-language
questions over your own documents. Upload PDFs, Word, or text files and get
grounded, source-cited answers — plus on-demand summaries — instead of reading
the whole document.

Built to work well on dense, domain-heavy documents (financial filings,
research notes, regulatory circulars, contracts), where answers must come
*from the document* rather than the model's memory.

**Live demo:** _<add deployed URL>_ · **Demo doc:** _<link a sample PDF you query in the demo>_

---

## What it does

- **Upload & parse** — PDF (PyMuPDF), DOCX (python-docx), and TXT.
- **Chunk & embed** — recursive character chunking; each chunk embedded locally
  with `all-MiniLM-L6-v2` (384-dim).
- **Retrieve** — cosine-similarity search over chunk embeddings with a
  query-length-aware threshold. If nothing clears the bar, retrieval returns no
  context so the model refuses rather than answering from unrelated text.
- **Generate** — Groq (`llama-3.1-8b-instant`) answers *grounded strictly in the
  retrieved chunks*, and is instructed to say when the document doesn't contain
  the answer (reduces hallucination).
- **Cite sources** — answers can return which document/chunk they came from.
- **Summarise** — one-click document summary alongside Q&A.

## Architecture

```
          upload                         query
            │                              │
     ┌──────▼───────┐              ┌───────▼────────┐
     │ extract text │              │ embed query    │  (local MiniLM / fastembed)
     │ (PDF/DOCX/TXT)│             └───────┬────────┘
     └──────┬───────┘                      │
     ┌──────▼───────┐              ┌────────▼─────────┐
     │ chunk (LC)   │              │ cosine retrieval │  top-k relevant chunks
     └──────┬───────┘              └────────┬─────────┘
     ┌──────▼───────────┐          ┌────────▼─────────┐
     │ embed (MiniLM)   │          │ prompt assembly  │  grounded, cited context
     └──────┬───────────┘          └────────┬─────────┘
     ┌──────▼───────┐              ┌─────────▼────────┐
     │ MongoDB      │◀─────────────│ Groq LLM answer  │
     │ (chunks+vec) │              └──────────────────┘
     └──────────────┘
```

**Stack:** React (Vite) · Flask · MongoDB · fastembed (ONNX, `all-MiniLM-L6-v2`) · Groq LLM · LangChain text-splitters · PyMuPDF

### Design notes
- **Local embeddings, no API keys.** Embeddings run locally via `fastembed`
  (ONNX runtime — no PyTorch), so there's no dependency on any external
  embedding API and the model has a small enough memory footprint to run on
  modest cloud instances. The model downloads and caches once on first run.
- **Grounded generation.** The LLM is constrained to the retrieved context and
  told to refuse when the answer isn't present — the anti-hallucination guard
  that matters most for document Q&A.
- **Honest refusal.** If no chunk clears the similarity threshold, the retriever
  returns nothing and the app says the answer isn't in the document, rather than
  fabricating one from weakly-related text. Answers that do ground out come back
  with citations (filename, chunk index, and match score) shown in the UI.

---

## Getting started

### Prerequisites
- Python 3.10+, Node 18+
- A MongoDB connection (Atlas free tier is fine)
- A free Groq API key — https://console.groq.com/keys

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then fill in GROQ_API_KEY, MONGO_URI, etc.
python app.py             # serves on http://localhost:5000
```
First run downloads the embedding model (~90 MB) and caches it locally.

### Frontend
```bash
cd frontend
npm install
# create frontend/.env with:  VITE_API_BASE_URL=http://localhost:5000
npm run dev
```

---

## API

| Method | Endpoint       | Body                                   | Returns                     |
|--------|----------------|----------------------------------------|-----------------------------|
| POST   | `/api/upload`  | multipart form: `file` (or `file0…`)   | `documentId`, `filename`    |
| POST   | `/api/query`   | `{ "message": "...", "document_ids": [...] }` | `{ "answer": "...", "sources"? }` |

---

## Deployment

- **Backend** (Render / Railway / Fly.io): start command `python app.py`
  (or `waitress-serve --port=$PORT app:app`). Set env vars from `.env.example`.
  Persist or allow the fastembed model cache on first boot.
- **Frontend** (Vercel): set `VITE_API_BASE_URL` to the deployed backend URL.
- **Database:** MongoDB Atlas.

---

## Roadmap
- Swap in-Python cosine search for MongoDB Atlas `$vectorSearch` at scale.
- Retrieval evaluation harness (hit-rate / MRR on a golden Q&A set).
- Cross-encoder reranking for higher precision on long documents.
