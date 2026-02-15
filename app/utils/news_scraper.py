import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("forex_service")

class NewsScraper:
    def __init__(self):
        """Initializes the scraper and the sentiment analyzer."""
        self.base_url = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        # Initialize the sentiment analyzer once
        self.analyzer = SentimentIntensityAnalyzer()

    async def get_news(self, query: str, limit: int = 5):
        """
        Fetches the latest news, analyzes sentiment, and returns an aggregate score.
        Returns a tuple: (list_of_news_items, average_sentiment_score)
        """
        loop = asyncio.get_running_loop()

        def fetch_and_analyze():
            try:
                url = self.base_url.format(query=query)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                try:
                    soup = BeautifulSoup(response.content, features="xml")
                except Exception:
                    soup = BeautifulSoup(response.content, features="html.parser")
                
                items = soup.find_all("item")
                news_list = []
                total_sentiment = 0.0
                
                for item in items[:limit]:
                    title = item.title.text if item.title else "No Title"
                    
                    # Perform sentiment analysis on the title
                    sentiment_scores = self.analyzer.polarity_scores(title)
                    compound_score = sentiment_scores['compound']
                    total_sentiment += compound_score
                    
                    news_list.append({
                        "title": title,
                        "link": item.link.text if item.link else "#",
                        "pub_date": item.pubDate.text if item.pubDate else "",
                        "sentiment_score": compound_score
                    })
                
                # Calculate the average sentiment
                average_sentiment = total_sentiment / len(news_list) if news_list else 0.0
                
                return news_list, average_sentiment

            except Exception as e:
                logger.error(f"News Scraping Error for '{query}': {e}")
                return [], 0.0

        # Run the blocking request and analysis in a separate thread
        return await loop.run_in_executor(None, fetch_and_analyze)