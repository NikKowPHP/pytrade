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
        Returns: (formatted_text, raw_headlines_list)
        """
        news_text = "RECENT NEWS:\n"
        raw_headlines = []
        has_news = False
        
        # 1. Try NewsAPI if key is present
        if self.news_api_key:
            try:
                self.logger.info(f"Fetching news from NewsAPI for {symbol}")
                query = symbol
                if len(symbol) == 6 and symbol.isalpha():
                     query = f"{symbol} OR {symbol[:3]} AND {symbol[3:]} forex"
                
                url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={self.news_api_key}"
                response = requests.get(url)
                data = response.json()
                
                if data.get("status") == "ok":
                    articles = data.get("articles", [])[:10]
                    if articles:
                        for article in articles:
                            title = article.get("title")
                            source = article.get("source", {}).get("name")
                            raw_headlines.append(f"{source}: {title}")
                            pub_date = article.get("publishedAt", "")[:10]
                            news_text += f"- [{pub_date}] ({source}) {title}\n"
                        has_news = True
            except Exception as e:
                self.logger.error(f"Error fetching from NewsAPI: {e}")

        # 2. Fallback to Yahoo Finance
        if not has_news or len(raw_headlines) < 3:
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
                        raw_headlines.append(f"Yahoo: {title}")
                        pub_date = content.get("pubDate", "")[:10]
                        news_text += f"- [{pub_date}] (Yahoo) {title}\n"
                    has_news = True
            except Exception as e:
                self.logger.error(f"Error fetching from Yahoo Finance: {e}")

        if not has_news:
             news_text += "No recent news found.\n"

        return news_text, raw_headlines

    def fetch_economic_calendar(self, symbol=None):
        """
        Fetches events and checks for imminent High Impact risks.
        Returns tuple: (formatted_text, warning_flag)
        """
        try:
            self.logger.info("Fetching Economic Calendar from ForexFactory")
            # Spoof User-Agent to avoid 403
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(self.ff_calendar_url, headers=headers)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Determine relevant currencies
            relevant_currencies = []
            if symbol and len(symbol) == 6:
                relevant_currencies = [symbol[:3], symbol[3:]] # e.g. ['EUR', 'USD']
            
            events_text = "ECONOMIC CALENDAR (This Week):\n"
            found_events = False
            
            # Risk Flag
            high_impact_imminent = False
            min_days_to_impact = 999
            now = datetime.now() # Server time (Make sure to align timezones in production)

            for event in root.findall('event'):
                country = event.find('country').text
                impact = event.find('impact').text
                title = event.find('title').text
                date_str = event.find('date').text # YYYY-MM-DD
                time_str = event.find('time').text # e.g. 8:30am
                
                # Filter by impact
                if impact not in ['High', 'Medium']:
                    continue
                
                # Filter by currency/country if relevant_currencies are set
                if relevant_currencies and country not in relevant_currencies:
                    continue

                # Formatting
                events_text += f"- [{date_str} {time_str}] ({country}) {title} [{impact}]\n"
                found_events = True
                
                # Check Time Delta for High Impact
                if impact == 'High':
                    try:
                        event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        today = now.date()
                        delta = (event_date - today).days
                        
                        if delta >= 0 and delta < min_days_to_impact:
                            min_days_to_impact = delta
                            
                        # LOGIC: Check if date is today
                        if date_str == now.strftime("%Y-%m-%d"):
                            events_text += "   !!! HIGH IMPACT EVENT TODAY !!!\n"
                            high_impact_imminent = True
                    except Exception:
                        pass
            
            if not found_events:
                 events_text += "No significant events found.\n"

            # Return specialized dictionary to support 'Clear Air' calculations
            risk_data = {
                'today': high_impact_imminent,
                'days_to_high_impact': min_days_to_impact if min_days_to_impact != 999 else "No events this week"
            }
            events_text += f"\nCLEAR AIR: {risk_data['days_to_high_impact']} days until next High Impact event.\n"
            
            return events_text, risk_data

        except Exception as e:
            if hasattr(e, 'response') and e.response.status_code == 429:
                self.logger.warning("ForexFactory Rate Limit (429).")
                return "Economic Calendar unavailable (Rate Limited).\n", {'today': False, 'days_to_high_impact': 'Unknown'}
            self.logger.error(f"Error fetching Economic Calendar: {e}")
            return "Error fetching calendar.\n", {'today': False, 'days_to_high_impact': 'Unknown'}
