from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_qdrant import QdrantVectorStore
from app.core.embeddings import load_embeddings
from app.core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)

COLLECTION_NAME = "multimodal_documents"

def ensure_collection():
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text": VectorParams(size=384, distance=Distance.COSINE),
                "image": VectorParams(size=512, distance=Distance.COSINE)
            }
        )

def get_vectorstore():
    ensure_collection()
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=load_embeddings(),
        vector_name="text"
    )