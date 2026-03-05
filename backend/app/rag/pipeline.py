from app.vectorstore.qdrant import get_vectorstore, client, COLLECTION_NAME
from app.search.web import web_search
from app.core.llm import load_llm
from app.multimodal.image import embed_text_for_image_search
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, NamedVector

vectorstore = get_vectorstore()
llm = load_llm()

def run_rag(query: str):
    # 1. First search local text vector store
    local_results = vectorstore.similarity_search_with_score(query, k=3)
    
    # 2. Search local image vector store
    image_query_vector = embed_text_for_image_search(query)
    try:
        image_results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=NamedVector("image", image_query_vector[0]),
            limit=2,
            with_payload=True,
            query_filter=Filter(
                must=[FieldCondition(key="type", match=MatchValue(value="image"))]
            )
        )
    except Exception as e:
        print(f"Error querying images: {e}")
        image_results = []
    
    internal_context = ""
    has_strong_match = False
    
    # Text matches
    for doc, score in local_results:
        source = doc.metadata.get("source", doc.metadata.get("path", "Unknown Local Source"))
        page = doc.metadata.get("page", "N/A")
        topic = doc.metadata.get("topic", "N/A")
        
        meta_str = f"[Source: {source}"
        if page != "N/A":
            meta_str += f", Page: {page}"
        if topic != "N/A":
            meta_str += f", Topic: {topic}"
        meta_str += "]"
        
        internal_context += f"{meta_str}\n{doc.page_content}\n\n"
        if score > 0.7:
            has_strong_match = True

    # Image matches
    for r in image_results:
        if r.score > 0.22:
            payload = r.payload
            source = payload.get("source", payload.get("path", "Unknown Local Image"))
            page = payload.get("page", "N/A")
            path = payload.get("path", "")
            
            meta_str = f"[Source: {source}"
            if page != "N/A":
                meta_str += f", Page: {page}"
            meta_str += f", Image Path: {path}]"
            
            internal_context += f"{meta_str}\n[This is a relevant image. You can embed it using Markdown syntax: ![Rendered Image](/{path})]\n\n"
            has_strong_match = True

    web_context = ""
    # 3. Conditional Web Search
    if not has_strong_match:
        try:
            web_results = web_search(query)
            for res in web_results:
                url = res.get("url", "Unknown URL")
                content = res.get("content", "")
                web_context += f"[Source: {url}]\n{content}\n\n"
        except Exception as e:
            web_context = f"Web search failed: {e}"
    
    full_context = f"Local Documents/Images:\n{internal_context}\n\nWeb Results:\n{web_context}"

    prompt = f"""
    You are a helpful Multimodal AI assistant. Answer the user's question using ONLY the provided context below.
    If the context does not contain the answer, say you don't know rather than making it up.
    
    CRITICAL: You MUST cite your sources accurately. For every fact you state, append the full citation tag found in the context.
    For example: [Source: uploaded_file.pdf, Page: 5, Topic: Machine Learning] or [Source: https://example.com].
    Ensure that the page number and main topic are always cited if available.
    
    If the context provides a relevant [Image Path: ...], you SHOULD include it in your response using markdown image syntax so the user can see it. 
    Example: ![Relevant Image](/temp_uploads/image.png)

    Context:
    {full_context}

    Question:
    {query}
    """

    response = llm.invoke(prompt)
    return response.content