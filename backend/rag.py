
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from groq import Groq
from google import genai
from google.genai import errors
from pypdf import PdfReader


# --------------------------------------------------
# 1. PROJECT PATHS AND ENVIRONMENT VARIABLES
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = Path(
    os.getenv("DOCUMENTS_DIR", str(PROJECT_ROOT / "documents"))
)
CHROMA_DIR = Path(
    os.getenv("CHROMA_DIR", str(PROJECT_ROOT / "chroma_db"))
)

load_dotenv(PROJECT_ROOT / ".env")


# --------------------------------------------------
# 2. GROQ CLIENT - ANSWER GENERATION
# --------------------------------------------------

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing from the project-root .env file."
    )

groq_client = Groq(api_key=groq_api_key)


# --------------------------------------------------
# 3. GEMINI CLIENT - TEXT EMBEDDINGS
# --------------------------------------------------

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from the project-root .env file."
    )

client = genai.Client(api_key=gemini_api_key)

EMBEDDING_MODEL = "gemini-embedding-001"
GROQ_GENERATION_MODEL = "openai/gpt-oss-20b"


# --------------------------------------------------
# 4. CHROMADB CONFIGURATION
# --------------------------------------------------

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = chroma_client.get_or_create_collection(
    name="climate_documents",
    metadata={"hnsw:space": "cosine"},
)


# --------------------------------------------------
# 5. TEXT CHUNKING
# --------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:

    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


# --------------------------------------------------
# 6. GENERATE EMBEDDINGS USING GEMINI
# --------------------------------------------------

def embed_text(text: str) -> list[float]:

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )

    if not response.embeddings:
        raise RuntimeError("Gemini returned no embedding.")

    return response.embeddings[0].values


# --------------------------------------------------
# 7. INDEX PDF DOCUMENTS
# --------------------------------------------------

def index_pdfs(
    pdf_paths: list[Path] | None = None,
    source_names: dict[Path, str] | None = None,
):

    print("Starting PDF indexing")
    print("Documents folder:", DOCUMENTS_DIR)
    print("Folder exists:", DOCUMENTS_DIR.exists())

    DOCUMENTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_files = pdf_paths if pdf_paths is not None else list(DOCUMENTS_DIR.glob("*.pdf"))

    print("PDFs found:", [p.name for p in pdf_files])

    if not pdf_files:
        return {
            "message": "No PDFs found. Add climate reports to documents/."
        }

    indexed_chunks = 0
    failed_files = []

    for pdf_path in pdf_files:

        try:
            reader = PdfReader(str(pdf_path))
            file_chunk_count = 0

            for page_number, page in enumerate(
                reader.pages,
                start=1,
            ):

                page_text = page.extract_text() or ""
                chunks = chunk_text(page_text)

                for chunk_number, chunk in enumerate(chunks):

                    record_id = (
                        f"{pdf_path.name}-p{page_number}-c{chunk_number}"
                    )

                    # Skip chunks that are already indexed
                    existing = collection.get(ids=[record_id])

                    if existing["ids"]:
                        file_chunk_count += 1
                        continue

                    embedding = embed_text(chunk)

                    collection.add(
                        ids=[record_id],
                        documents=[chunk],
                        embeddings=[embedding],
                        metadatas=[{
                            "source": (source_names or {}).get(
                                pdf_path, pdf_path.name
                            ),
                            "page": page_number,
                        }],
                    )

                    indexed_chunks += 1
                    file_chunk_count += 1

            if file_chunk_count == 0:
                failed_files.append({
                    "file": pdf_path.name,
                    "error": "No extractable text found in this PDF.",
                })

        except errors.APIError as exc:

            print(
                f"Gemini API error while indexing "
                f"{pdf_path.name}: {exc}"
            )

            if getattr(exc, "code", None) == 429:
                return {
                    "message": (
                        "Gemini embedding quota exceeded. "
                        "Check your API quota and retry when available."
                    ),
                    "new_chunks_indexed": indexed_chunks,
                    "total_chunks_in_database": collection.count(),
                }

            failed_files.append({
                "file": pdf_path.name,
                "error": str(exc),
            })

        except Exception as exc:

            print(f"Error indexing {pdf_path.name}: {exc}")

            failed_files.append({
                "file": pdf_path.name,
                "error": str(exc),
            })

    return {
        "message": "PDF indexing finished.",
        "new_chunks_indexed": indexed_chunks,
        "total_chunks_in_database": collection.count(),
        "failed_files": failed_files,
    }


# --------------------------------------------------
# 8. ASK CLIMATE QUESTIONS
# --------------------------------------------------

def ask_climate_question(question: str):

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    if collection.count() == 0:
        return {
            "answer": (
                "The climate document library is empty. "
                "Add PDFs and index them before asking questions."
            ),
            "sources": [],
        }

    # Step 1: Convert the question into an embedding
    query_embedding = embed_text(question)

    # Step 2: Retrieve relevant PDF chunks from ChromaDB
    matches = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(4, collection.count()),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = matches["documents"][0] or []
    metadatas = matches["metadatas"][0] or []

    context_parts = []
    sources = []

    # Step 3: Prepare context and source information
    for document, metadata in zip(documents, metadatas):

        source = metadata.get("source", "Unknown source")
        page = metadata.get("page", "Unknown page")

        context_parts.append(
            f"Source: {source}, page {page}\n{document}"
        )

        source_entry = {
            "source": source,
            "page": page,
        }

        if source_entry not in sources:
            sources.append(source_entry)

    if not context_parts:
        return {
            "answer": "No relevant document content was retrieved.",
            "sources": [],
        }

    context = "\n\n".join(context_parts)

    # Step 4: Generate the answer using Groq
    response = groq_client.chat.completions.create(
        model=GROQ_GENERATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a climate information assistant. "
                    "Answer using only the retrieved document context. "
                    "If the evidence is insufficient, say so clearly. "
                    "Do not invent facts, page numbers, or citations. "
                    "Be clear and helpful."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Retrieved context:\n{context}\n\n"
                    f"User question: {question}"
                ),
            },
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer or "The model returned an empty answer.",
        "sources": sources,
    }
