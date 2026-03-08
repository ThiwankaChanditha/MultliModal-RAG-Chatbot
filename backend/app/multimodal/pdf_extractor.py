import fitz
import pdfplumber
import os
import uuid
from PIL import Image
import io

def extract_images_from_pdf(pdf_path: str, output_dir: str) -> list[dict]:
    """
    Extract images from PDF pages.
    Returns list of dicts: {doc_id, path, page, source}
    """
    results = []
    doc = fitz.open(pdf_path)
    source = os.path.basename(pdf_path)

    for page_num, page in enumerate(doc):
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            # Skip tiny images (icons, decorations) — under 5KB
            if len(image_bytes) < 5000:
                continue

            doc_id = f"img_{uuid.uuid4().hex[:12]}"
            img_filename = f"{doc_id}.{image_ext}"
            img_filepath = os.path.join(output_dir, img_filename)

            with open(img_filepath, "wb") as f:
                f.write(image_bytes)

            results.append({
                "doc_id": doc_id,
                "path": img_filepath,
                "page": page_num + 1,
                "source": source,
                "type": "image",
            })

    doc.close()
    return results


def extract_tables_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract tables from PDF using pdfplumber.
    Returns list of dicts: {doc_id, markdown_table, page, source}
    """
    results = []
    source = os.path.basename(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table_index, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue

                # Convert to markdown
                markdown = _table_to_markdown(table)
                if not markdown.strip():
                    continue

                doc_id = f"tbl_{uuid.uuid4().hex[:12]}"
                results.append({
                    "doc_id": doc_id,
                    "markdown_table": markdown,
                    "page": page_num + 1,
                    "source": source,
                    "type": "table",
                })

    return results


def _table_to_markdown(table: list[list]) -> str:
    """Convert pdfplumber table (list of lists) to markdown string."""
    if not table:
        return ""

    # Clean cells
    def clean(cell):
        if cell is None:
            return ""
        return str(cell).replace("\n", " ").strip()

    rows = [[clean(cell) for cell in row] for row in table]
    header = rows[0]
    body = rows[1:]

    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in body:
        # Pad row if it has fewer cells than header
        while len(row) < len(header):
            row.append("")
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)