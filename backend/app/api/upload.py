from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import shutil
import os
import uuid
from langchain_core.documents import Document

from app.vectorstore.qdrant import get_vectorstore, client, COLLECTION_NAME
from app.multimodal.image import embed_image
from app.multimodal.pdf_extractor import extract_images_from_pdf, extract_tables_from_pdf
from app.multimodal.summarizer import summarize_image, summarize_table
from app.core.llm import load_llm
from app.core.auth import verify_token
from qdrant_client.models import PointStruct
import fitz

router = APIRouter()
os.makedirs("temp_uploads", exist_ok=True)


def _store_image_with_summary(
    image_path: str,
    doc_id: str,
    source: str,
    page: int,
    summary: str,
):
    """
    Store an image in two ways:
    1. Text vector (384d) of its GPT summary → found by semantic text search
    2. Image vector (512d) CLIP embedding   → found by visual similarity search
    Both share the same doc_id so we can link them at query time.
    """
    # Get a fresh vectorstore instance every call so indexes are always ready
    vs = get_vectorstore()

    # 1. Store text summary as a text-vector document
    summary_doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "type": "image_summary",
            "path": image_path,
            "source": source,
            "page": page,
        },
    )
    vs.add_documents([summary_doc])
    print(f"Stored image_summary: doc_id={doc_id}, source={source}, page={page}")

    # 2. Store raw CLIP image vector
    img_embedding = embed_image(image_path)
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector={"image": img_embedding[0]},
                payload={
                    "doc_id": doc_id,
                    "type": "image",
                    "path": image_path,
                    "page_content": summary,
                    "source": source,
                    "page": page,
                },
            )
        ],
    )
    print(f"Stored image vector: doc_id={doc_id}, path={image_path}")


def _store_table_with_summary(
    markdown_table: str,
    doc_id: str,
    source: str,
    page: int,
    summary: str,
):
    vs = get_vectorstore()

    summary_doc = Document(
        page_content=summary,
        metadata={
            "doc_id": doc_id,
            "type": "table_summary",
            "source": source,
            "page": page,
        },
    )
    raw_doc = Document(
        page_content=f"Table from {source} page {page}:\n{markdown_table}",
        metadata={
            "doc_id": doc_id,
            "type": "table_raw",
            "source": source,
            "page": page,
            "markdown_table": markdown_table,
        },
    )
    vs.add_documents([summary_doc, raw_doc])
    print(f"Stored table: doc_id={doc_id}, source={source}, page={page}")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(verify_token)):
    try:
        file_location = f"temp_uploads/{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        # ── Image upload ──────────────────────────────────────────────────
        if file.content_type and file.content_type.startswith("image/"):
            doc_id = f"img_{uuid.uuid4().hex[:12]}"
            print(f"Summarizing uploaded image: {file.filename}")
            summary = summarize_image(file_location, file.filename, page=1)
            print(f"Summary: {summary[:100]}")
            _store_image_with_summary(file_location, doc_id, file.filename, 1, summary)
            return {
                "message": f"Uploaded and indexed image: {file.filename}",
                "type": "image",
                "doc_id": doc_id,
                "summary": summary,
            }

        # ── Plain text upload ─────────────────────────────────────────────
        elif file.filename.endswith(".txt"):
            vs = get_vectorstore()
            with open(file_location, "r", encoding="utf-8") as f:
                content = f.read()
            doc = Document(
                page_content=content,
                metadata={"source": file.filename, "type": "text"},
            )
            vs.add_documents([doc])
            return {
                "message": f"Uploaded and indexed: {file.filename}",
                "type": "text",
            }

        # ── PDF upload ────────────────────────────────────────────────────
        elif file.filename.endswith(".pdf"):
            vs = get_vectorstore()
            llm = load_llm()
            stats = {"text_pages": 0, "images": 0, "tables": 0}

            # --- Text pages ---
            fitz_doc = fitz.open(file_location)
            langchain_docs = []
            for i, page in enumerate(fitz_doc):
                content = page.get_text().strip()
                if not content:
                    continue
                try:
                    topic_prompt = (
                        f"Extract a very short 2-4 word main topic from this text. "
                        f"Respond ONLY with the topic.\n\nText:\n{content[:1000]}"
                    )
                    topic = llm.invoke(topic_prompt).content.strip()
                except Exception:
                    topic = "General"

                langchain_docs.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file.filename,
                            "page": i + 1,
                            "topic": topic,
                            "type": "text",
                        },
                    )
                )
            fitz_doc.close()

            if langchain_docs:
                vs.add_documents(langchain_docs)
                stats["text_pages"] = len(langchain_docs)
                print(f"Stored {len(langchain_docs)} text pages")

            # --- Images ---
            images = extract_images_from_pdf(file_location, "temp_uploads")
            print(f"Found {len(images)} images in PDF")
            for img_info in images:
                try:
                    print(f"Summarizing image: {img_info['path']}")
                    summary = summarize_image(
                        img_info["path"], img_info["source"], img_info["page"]
                    )
                    print(f"Image summary: {summary[:100]}")
                    _store_image_with_summary(
                        img_info["path"],
                        img_info["doc_id"],
                        img_info["source"],
                        img_info["page"],
                        summary,
                    )
                    stats["images"] += 1
                except Exception as e:
                    print(f"Failed to process image {img_info['path']}: {e}")

            # --- Tables ---
            tables = extract_tables_from_pdf(file_location)
            print(f"Found {len(tables)} tables in PDF")
            for tbl_info in tables:
                try:
                    summary = summarize_table(
                        tbl_info["markdown_table"],
                        tbl_info["source"],
                        tbl_info["page"],
                    )
                    _store_table_with_summary(
                        tbl_info["markdown_table"],
                        tbl_info["doc_id"],
                        tbl_info["source"],
                        tbl_info["page"],
                        summary,
                    )
                    stats["tables"] += 1
                except Exception as e:
                    print(f"Failed to process table: {e}")

            return {
                "message": (
                    f"Processed {file.filename}: "
                    f"{stats['text_pages']} text pages, "
                    f"{stats['images']} images, "
                    f"{stats['tables']} tables"
                ),
                "type": "pdf",
                "stats": stats,
            }

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use PDF, image, or .txt"
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))