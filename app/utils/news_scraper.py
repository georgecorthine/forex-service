import asyncio
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("forex_service")

class NewsScraper:
    def __init__(self):
        # Google News RSS is a reliable source for scraping specific topics
        self.base_url = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    async def get_news(self, query: str, limit: int = 3):
        """
        Fetches the latest news headlines for a specific query.
        """
        loop = asyncio.get_running_loop()

        def fetch_and_parse():
            try:
                url = self.base_url.format(query=query)
                # User-Agent is often required to avoid basic bot detection
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Try parsing with xml first (requires lxml), fallback to html.parser
                try:
                    soup = BeautifulSoup(response.content, features="xml")
                except Exception:
                    soup = BeautifulSoup(response.content, features="html.parser")
                
                items = soup.find_all("item")
                news_list = []
                
                for item in items[:limit]:
                    news_list.append({
                        "title": item.title.text if item.title else "No Title",
                        "link": item.link.text if item.link else "#",
                        "pub_date": item.pubDate.text if item.pubDate else ""
                    })
                return news_list

            except Exception as e:
                logger.error(f"News Scraping Error for '{query}': {e}")
                return []

        # Run the blocking request in a separate thread
        return await loop.run_in_executor(None, fetch_and_parse)