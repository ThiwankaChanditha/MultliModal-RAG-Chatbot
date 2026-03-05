from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import fitz
from app.vectorstore.qdrant import get_vectorstore, client, COLLECTION_NAME
from qdrant_client.models import PointStruct
import uuid
from app.multimodal.image import embed_image
from langchain_core.documents import Document

router = APIRouter()
vectorstore = get_vectorstore()
os.makedirs("temp_uploads", exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"temp_uploads/{file.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        if file.content_type and file.content_type.startswith("image/"):
            embedding = embed_image(file_location)
            
            point_id = str(uuid.uuid4())
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector={"image": embedding[0]},
                        payload={"type": "image", "path": file_location, "page_content": f"[Image Uploaded: {file.filename}]", "source": file.filename}
                    )
                ]
            )
            return {"message": f"Successfully uploaded image {file.filename}", "type": "image"}
            
        elif file.filename.endswith(".txt"):
            with open(file_location, "r", encoding="utf-8") as f:
                content = f.read()
            doc = Document(page_content=content, metadata={"source": file.filename})
            vectorstore.add_documents([doc])
            return {"message": f"Successfully uploaded and indexed text file {file.filename}", "type": "text"}
            
        elif file.filename.endswith(".pdf"):
            doc = fitz.open(file_location)
            langchain_docs = []
            from app.core.llm import load_llm
            topic_llm = load_llm()
            
            pdf_images_count = 0
            
            for i, page in enumerate(doc):
                # Extract images
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    img_filename = f"{file.filename}_page{i+1}_img{img_index}.{image_ext}"
                    img_filepath = f"temp_uploads/{img_filename}"
                    
                    with open(img_filepath, "wb") as f:
                        f.write(image_bytes)
                        
                    img_embedding = embed_image(img_filepath)
                    point_id = str(uuid.uuid4())
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[
                            PointStruct(
                                id=point_id,
                                vector={"image": img_embedding[0]},
                                payload={"type": "image", "path": img_filepath, "page_content": f"[Image Extracted from {file.filename}, Page {i+1}]", "source": file.filename, "page": i+1}
                            )
                        ]
                    )
                    pdf_images_count += 1
                    
                content = page.get_text().strip()
                if not content:
                    continue
                
                try:
                    topic_prompt = f"Extract a very short 2-4 word main topic from this text. Respond ONLY with the topic.\n\nText:\n{content[:1000]}"
                    topic = topic_llm.invoke(topic_prompt).content.strip()
                except:
                    topic = "General"
                    
                langchain_docs.append(Document(
                    page_content=content,
                    metadata={"source": file.filename, "page": i + 1, "topic": topic}
                ))
            
            if langchain_docs:
                vectorstore.add_documents(langchain_docs)
            return {"message": f"Successfully uploaded parsed PDF {file.filename} ({len(langchain_docs)} text pages, {pdf_images_count} images)", "type": "pdf"}
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass
