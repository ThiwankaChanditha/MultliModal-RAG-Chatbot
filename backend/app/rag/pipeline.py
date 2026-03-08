from app.vectorstore.qdrant import get_vectorstore, client, COLLECTION_NAME
from app.search.web import web_search
from app.core.llm import load_llm
from app.multimodal.image import embed_text_for_image_search
from qdrant_client.models import Filter, FieldCondition, MatchValue

vectorstore = get_vectorstore()
llm = load_llm()

_VISUAL_KEYWORDS = {
    "image", "images", "figure", "figures", "fig", "chart", "charts",
    "graph", "graphs", "diagram", "diagrams", "plot", "plots", "table",
    "tables", "illustration", "illustrations", "photo", "photos",
    "picture", "pictures", "show", "display", "visuali", "visual",
    "draw", "drawing", "architecture", "flowchart", "pipeline",
    "screenshot", "model", "structure", "layout",
}


def _is_visual_query(query: str) -> bool:
    """
    Returns True only if the query is likely asking about visual content.
    Checks for visual keywords and explicit figure/image references.
    """
    q_lower = query.lower()

    import re
    if re.search(r"\b(fig(ure)?\.?\s*\d+|image\s*\d+|table\s*\d+)\b", q_lower):
        return True
    words = set(re.split(r"\W+", q_lower))

    if words & _VISUAL_KEYWORDS:
        return True

    for kw in _VISUAL_KEYWORDS:
        if kw in q_lower:
            return True

    return False


def _get_linked_image(doc_id: str) -> dict | None:
    try:
        results, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                    FieldCondition(key="type", match=MatchValue(value="image")),
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )
        if results:
            return results[0].payload
    except Exception as e:
        print(f"doc_id image lookup failed: {e}")
    return None


def _search_images_by_text(query_vector: list) -> list:
    try:
        result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using="image",
            limit=3,
            with_payload=True,
            query_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="image"))]
            ),
        )
        return result.points if hasattr(result, "points") else []
    except Exception as e:
        print(f"Image vector search error: {e}")
        return []


def _images_are_relevant(query: str, image_summaries: list[str]) -> bool:
    """
    Ask the LLM whether the retrieved images are actually relevant to the query.
    Only called when we have candidate images, to avoid unnecessary LLM calls.
    Returns True if at least one image is relevant.
    """
    if not image_summaries:
        return False

    summaries_text = "\n".join(
        f"- Image {i+1}: {s}" for i, s in enumerate(image_summaries)
    )

    prompt = (
        f"A user asked: \"{query}\"\n\n"
        f"The following images were retrieved from the document:\n{summaries_text}\n\n"
        "Are any of these images directly relevant to answering the user's question? "
        "Answer with only YES or NO."
    )

    try:
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False


def run_rag(query: str) -> str:
    internal_context = ""
    has_strong_match = False
    image_candidates = []   # list of (path, summary, source, page)

    visual_query = _is_visual_query(query)
    print(f"Visual query: {visual_query} | Query: {query}")

    # ── 1. Text vector search ─────────────────────────────────────────────
    local_results = vectorstore.similarity_search_with_score(query, k=5)

    for doc, score in local_results:
        meta = doc.metadata
        source = meta.get("source", "Unknown")
        page = meta.get("page", "N/A")
        topic = meta.get("topic", "")
        doc_type = meta.get("type", "text")
        doc_id = meta.get("doc_id", "")

        meta_parts = [f"Source: {source}"]
        if page != "N/A":
            meta_parts.append(f"Page: {page}")
        if topic:
            meta_parts.append(f"Topic: {topic}")
        if doc_type in ("image_summary", "table_summary", "table_raw"):
            meta_parts.append(f"Type: {doc_type}")
        meta_str = "[" + ", ".join(meta_parts) + "]"

        internal_context += f"{meta_str}\n{doc.page_content}\n\n"

        if score > 0.65:
            has_strong_match = True

        # Image summary hit — only collect if this is a visual query
        if visual_query and doc_type == "image_summary" and doc_id and score > 0.35:
            img_payload = _get_linked_image(doc_id)
            if img_payload:
                path = img_payload.get("path", "")
                existing = [p for p, _, _, _ in image_candidates]
                if path and path not in existing:
                    image_candidates.append((path, doc.page_content, source, page))
                    has_strong_match = True

        # Table summary — always pull raw markdown regardless of visual flag
        if doc_type == "table_summary" and doc_id:
            try:
                raw_results, _ = client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                            FieldCondition(key="type", match=MatchValue(value="table_raw")),
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )
                if raw_results:
                    raw_table = raw_results[0].payload.get("markdown_table", "")
                    if raw_table:
                        internal_context += f"[Raw Table Data, {meta_str}]\n{raw_table}\n\n"
            except Exception as e:
                print(f"Table raw fetch failed: {e}")

    # ── 2. CLIP image search — only for visual queries ────────────────────
    if visual_query:
        try:
            image_query_vector = embed_text_for_image_search(query)
            image_results = _search_images_by_text(image_query_vector[0])

            for r in image_results:
                score = r.score if hasattr(r, "score") else 0
                payload = r.payload if hasattr(r, "payload") else {}
                print(f"CLIP score: {score:.4f} | path: {payload.get('path', 'N/A')}")

                if score > 0.18:
                    path = payload.get("path", "")
                    existing = [p for p, _, _, _ in image_candidates]
                    if path and path not in existing:
                        summary = payload.get("page_content", "")
                        source = payload.get("source", path)
                        page = payload.get("page", "N/A")
                        image_candidates.append((path, summary, source, page))
                        internal_context += (
                            f"[Source: {source}, Page: {page}, Type: image]\n"
                            f"{summary}\n\n"
                        )
                        has_strong_match = True
        except Exception as e:
            print(f"Image search outer error: {e}")
    else:
        print("Skipping CLIP image search — not a visual query")

    # ── 3. Relevance filter — ask LLM if images actually answer the query ─
    # Only do this check if we have candidates AND it's borderline
    # (i.e. the query is visual but images might still be off-topic)
    image_paths_to_show = []
    if image_candidates:
        summaries = [s for _, s, _, _ in image_candidates]
        if _images_are_relevant(query, summaries):
            image_paths_to_show = image_candidates
            print(f"LLM confirmed {len(image_paths_to_show)} images are relevant")
        else:
            print("LLM determined images are NOT relevant to this query — skipping")

    # ── 4. Web search fallback ────────────────────────────────────────────
    web_context = ""
    if not has_strong_match:
        try:
            web_results = web_search(query)
            for res in web_results:
                url = res.get("url", "Unknown URL")
                content = res.get("content", "")
                web_context += f"[Source: {url}]\n{content}\n\n"
        except Exception as e:
            web_context = f"Web search failed: {e}"

    # ── 5. Build image context block for prompt ───────────────────────────
    image_context_block = ""
    if image_paths_to_show:
        image_context_block = "RETRIEVED IMAGES (relevant to this question, will be shown to user):\n"
        for i, (path, summary, source, page) in enumerate(image_paths_to_show, 1):
            image_context_block += (
                f"  Image {i}: from {source}, page {page}\n"
                f"  Description: {summary}\n\n"
            )

    # ── 6. Prompt ─────────────────────────────────────────────────────────
    full_context = (
        f"Local Documents/Images/Tables:\n{internal_context}\n\n"
        f"{image_context_block}"
        f"Web Results:\n{web_context}"
    )

    prompt = f"""You are a helpful Multimodal AI assistant.

    Answer the user's question using the context below.
    {"If relevant images were retrieved (listed under RETRIEVED IMAGES), describe what they show in your answer." if image_paths_to_show else ""}

    CITATION RULES:
    - After every fact, cite the source, e.g. [Source: file.pdf, Page: 3]
    - For web results, cite the URL.

    TABLE RULES:
    - If a table is in the context, render it as a markdown table.

    Context:
    {full_context}

    Question:
    {query}
    """

    response = llm.invoke(prompt)
    answer = response.content

    # ── 7. Append confirmed-relevant images after the answer ──────────────
    if image_paths_to_show:
        answer += "\n\n**Relevant Images:**\n"
        for path, summary, source, page in image_paths_to_show:
            if path:
                url_path = path.replace("\\", "/")
                if url_path.startswith("temp_uploads/"):
                    url_path = "/" + url_path
                elif not url_path.startswith("/"):
                    url_path = "/" + url_path
                answer += f"\n![{summary[:60]}]({url_path})\n"

    return answer