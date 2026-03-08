from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PayloadSchemaType,
)
from langchain_qdrant import QdrantVectorStore
from app.core.embeddings import load_embeddings
from app.core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)

COLLECTION_NAME = "multimodal_documents"

TEXT_VECTOR_SIZE = 384   # all-MiniLM-L6-v2
IMAGE_VECTOR_SIZE = 512  # clip-vit-base-patch32


def ensure_collection():
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text": VectorParams(size=TEXT_VECTOR_SIZE, distance=Distance.COSINE),
                "image": VectorParams(size=IMAGE_VECTOR_SIZE, distance=Distance.COSINE),
            }
        )

    # Create payload indexes so filtering works without error
    # These are idempotent — safe to call even if index already exists
    _ensure_payload_index("type")
    _ensure_payload_index("doc_id")
    _ensure_payload_index("source")


def _ensure_payload_index(field_name: str):
    try:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        # Index already exists — this is fine, just ignore
        err_str = str(e).lower()
        if "already exists" in err_str or "conflict" in err_str or "400" in err_str:
            pass
        else:
            print(f"Warning: could not create index for '{field_name}': {e}")


def get_vectorstore():
    ensure_collection()
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=load_embeddings(),
        vector_name="text",
    )