from langchain_openai import ChatOpenAI
from app.core.config import settings

def load_llm():
    return ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY, 
        model_name="gpt-4o-mini",                
        streaming=True,                          
        temperature=0                            
    )