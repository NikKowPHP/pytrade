import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import yfinance as yf
from config import NEWS_API_KEY
from services.logger import Logger

class NewsService:
    def __init__(self):
        self.logger = Logger()
        self.news_api_key = NEWS_API_KEY
        self.ff_calendar_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

    def fetch_news(self, symbol):
        """
        Fetches news for a given symbol.
        Tries NewsAPI first, falls back to Yahoo Finance.
        Returns a formatted string summary of the news.
        """
        news_text = "RECENT NEWS:\n"
        has_news = False
        
        # 1. Try NewsAPI if key is present
        if self.news_api_key:
            try:
                self.logger.info(f"Fetching news from NewsAPI for {symbol}")
                # Heuristic for Forex pairs to get relevant news
                query = symbol
                if len(symbol) == 6 and symbol.isalpha():
                     # e.g. "EURUSD" OR "EUR USD" OR "forex"
                     query = f"{symbol} OR {symbol[:3]} AND {symbol[3:]} forex"
                
                url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={self.news_api_key}"
                response = requests.get(url)
                data = response.json()
                
                if data.get("status") == "ok":
                    articles = data.get("articles", [])[:5] # Top 5
                    if articles:
                        for article in articles:
                            title = article.get("title")
                            description = article.get("description")
                            source = article.get("source", {}).get("name")
                            pub_date = article.get("publishedAt", "")[:10]
                            news_text += f"- [{pub_date}] ({source}) {title}: {description}\n"
                        has_news = True
                        return news_text # Return immediately if success
                    else:
                        self.logger.info("No articles found on NewsAPI.")
                else:
                    self.logger.warning(f"NewsAPI error: {data.get('message')}")

            except Exception as e:
                self.logger.error(f"Error fetching from NewsAPI: {e}")

        # 2. Fallback to Yahoo Finance
        try:
            self.logger.info(f"Fetching news from Yahoo Finance for {symbol}")
            ticker_symbol = symbol
            if not symbol.endswith('=X') and len(symbol) == 6:
                ticker_symbol = f"{symbol}=X"
            
            ticker = yf.Ticker(ticker_symbol)
            news_items = ticker.news
            
            if news_items:
                for item in news_items[:5]:
                    content = item.get("content", {})
                    title = content.get("title")
                    summary = content.get("summary")
                    pub_date = content.get("pubDate", "")[:10] # simple date slice
                    news_text += f"- [{pub_date}] (Yahoo) {title}: {summary}\n"
                has_news = True
            else:
                self.logger.info("No recent news found on Yahoo Finance.")
                
        except Exception as e:
            self.logger.error(f"Error fetching from Yahoo Finance: {e}")

        if not has_news:
             news_text += "No recent news found.\n"

        return news_text

    def fetch_economic_calendar(self, symbol=None):
        """
        Fetches economic calendar events from ForexFactory XML.
        Filters by currency if symbol is provided (e.g. EURUSD -> EUR, USD).
        Returns a formatted string summary of high/medium impact events.
        """
        try:
            self.logger.info("Fetching Economic Calendar from ForexFactory")
            # Spoof User-Agent to avoid 403
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(self.ff_calendar_url, headers=headers)
            response.raise_for_status()
            
            # The XML structure from FF is roughly:
            # <weeklyevents>
            #   <event>
            #     <title>...</title>
            #     <country>USD</country>
            #     <date>2026-02-17</date>
            #     <time>8:30am</time>
            #     <impact>High</impact>
            #   </event>
            # </weeklyevents>

            root = ET.fromstring(response.content)
            
            # Determine relevant currencies
            relevant_currencies = []
            if symbol and len(symbol) == 6:
                relevant_currencies = [symbol[:3], symbol[3:]] # e.g. ['EUR', 'USD']
            
            events_text = "ECONOMIC CALENDAR events (This Week):\n"
            found_events = False

            for event in root.findall('event'):
                country = event.find('country').text
                impact = event.find('impact').text
                title = event.find('title').text
                date_str = event.find('date').text
                time_str = event.find('time').text
                
                # Filter by impact
                if impact not in ['High', 'Medium']:
                    continue
                
                # Filter by currency/country if relevant_currencies are set
                # Note: FF uses currency codes in <country> (e.g. 'USD', 'EUR')
                if relevant_currencies and country not in relevant_currencies:
                    continue

                events_text += f"- [{date_str} {time_str}] ({country}) {title} [{impact}]\n"
                found_events = True
            
            if not found_events:
                 events_text += "No high/medium impact events found for these currencies this week.\n"

            return events_text

        except Exception as e:
            self.logger.error(f"Error fetching Economic Calendar: {e}")
            return "Error fetching Economic Calendar.\n"
