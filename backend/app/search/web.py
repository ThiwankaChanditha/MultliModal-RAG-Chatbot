from tavily import TavilyClient
from app.core.config import settings

client = TavilyClient(api_key=settings.TAVILY_API_KEY)

def web_search(query: str):
    res = client.search(query)
    return res["results"]