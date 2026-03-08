import base64
from app.core.llm import load_llm
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


def summarize_image(image_path: str, source: str, page: int) -> str:
    """
    Use GPT-4o-mini vision to generate a text summary of an image.
    This summary is what gets embedded as a text vector for retrieval.
    """
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Determine media type
        ext = image_path.rsplit(".", 1)[-1].lower()
        media_type_map = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif",
            "webp": "image/webp",
        }
        media_type = media_type_map.get(ext, "image/png")

        # Use vision-capable model
        vision_llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0,
            max_tokens=300,
        )

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        f"This image was extracted from '{source}', page {page}. "
                        "Describe it in 2-4 sentences, focusing on what data, "
                        "concepts, or visual information it contains. "
                        "Be specific so it can be found by semantic search."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_data}",
                        "detail": "low",
                    },
                },
            ]
        )

        response = vision_llm.invoke([message])
        return response.content.strip()

    except Exception as e:
        print(f"Image summarization failed for {image_path}: {e}")
        return f"[Image from {source}, page {page} — summary unavailable]"


def summarize_table(markdown_table: str, source: str, page: int) -> str:
    """
    Use GPT-4o-mini to generate a text summary of a table.
    """
    try:
        llm = load_llm()
        prompt = (
            f"The following table was extracted from '{source}', page {page}.\n\n"
            f"{markdown_table}\n\n"
            "In 2-3 sentences, describe what this table shows, including column names "
            "and any notable data patterns. Be specific for semantic search."
        )
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        print(f"Table summarization failed: {e}")
        return f"[Table from {source}, page {page} — summary unavailable]"