from fastapi import APIRouter
from app.vectorstore.qdrant import client, COLLECTION_NAME, get_vectorstore
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

router = APIRouter()


@router.get("/debug/collection-info")
def collection_info():
    info = client.get_collection(COLLECTION_NAME)
    # Safely extract whatever attributes exist on this qdrant-client version
    result = {
        "status": str(info.status),
        "points_count": info.points_count,
        "vector_config": {},
    }

    # vectors_count was removed in newer versions — use points_count instead
    try:
        result["vectors_count"] = info.vectors_count
    except AttributeError:
        result["vectors_count"] = "N/A (use points_count)"

    # Extract vector config safely
    try:
        vectors = info.config.params.vectors
        if isinstance(vectors, dict):
            result["vector_config"] = {
                name: {"size": v.size, "distance": str(v.distance)}
                for name, v in vectors.items()
            }
        else:
            result["vector_config"] = str(vectors)
    except Exception as e:
        result["vector_config"] = f"Could not parse: {e}"

    return result


@router.get("/debug/images")
def list_images():
    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="type", match=MatchValue(value="image"))]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False,
    )
    return [
        {
            "doc_id": p.payload.get("doc_id"),
            "path": p.payload.get("path"),
            "source": p.payload.get("source"),
            "page": p.payload.get("page"),
            "summary_preview": p.payload.get("page_content", "")[:150],
        }
        for p in results
    ]


@router.get("/debug/image-summaries")
def list_image_summaries():
    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="type", match=MatchValue(value="image_summary"))]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False,
    )
    return [
        {
            "doc_id": p.payload.get("doc_id"),
            "source": p.payload.get("source"),
            "page": p.payload.get("page"),
            "summary": p.payload.get("page_content", "")[:200],
        }
        for p in results
    ]


@router.get("/debug/tables")
def list_tables():
    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="type", match=MatchValue(value="table_summary"))]
        ),
        limit=10,
        with_payload=True,
        with_vectors=False,
    )
    return [
        {
            "doc_id": p.payload.get("doc_id"),
            "source": p.payload.get("source"),
            "page": p.payload.get("page"),
            "summary": p.payload.get("page_content", "")[:200],
        }
        for p in results
    ]


@router.get("/debug/search-test")
def search_test(q: str = "chart"):
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(q, k=5)
    return [
        {
            "score": round(score, 4),
            "type": doc.metadata.get("type"),
            "doc_id": doc.metadata.get("doc_id"),
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page"),
            "preview": doc.page_content[:150],
        }
        for doc, score in results
    ]


@router.get("/debug/clip-search-test")
def clip_search_test(q: str = "chart"):
    """Test CLIP image vector search directly."""
    from app.multimodal.image import embed_text_for_image_search

    query_vector = embed_text_for_image_search(q)

    try:
        result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector[0],
            using="image",
            limit=5,
            with_payload=True,
            query_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="image"))]
            ),
        )
        points = result.points if hasattr(result, "points") else []
        return [
            {
                "score": round(p.score, 4),
                "doc_id": p.payload.get("doc_id"),
                "path": p.payload.get("path"),
                "source": p.payload.get("source"),
                "page": p.payload.get("page"),
                "summary_preview": p.payload.get("page_content", "")[:150],
            }
            for p in points
        ]
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug/all-types")
def all_types():
    """Show a count of each document type stored in the collection."""
    type_counts = {}
    for type_val in ["text", "image", "image_summary", "table_summary", "table_raw"]:
        try:
            results, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value=type_val))]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            # scroll doesn't give total count — use count endpoint
            count_result = client.count(
                collection_name=COLLECTION_NAME,
                count_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value=type_val))]
                ),
                exact=True,
            )
            type_counts[type_val] = count_result.count
        except Exception as e:
            type_counts[type_val] = f"error: {e}"

    return type_counts