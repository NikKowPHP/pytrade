import os
import sys
import argparse
import requests
import json
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import Database
from services.market_data import MarketDataProvider
from services.scanner_service import ScannerService
from services.ai_service import AITrader
from services.config_manager import ConfigManager
from services.csm_service import CSMService

class DailyEODScanner:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL")
        self.market_data = MarketDataProvider()
        self.ai_trader = AITrader()
        self.scanner = ScannerService(self.market_data)
        self.scanner.ai_service = self.ai_trader
        self.config_manager = ConfigManager()
        self.csm_service = CSMService()
        self.db = Database()
        
    def run_scan(self):
        print(f"[{datetime.now()}] Starting EOD Market Scan (1D Timeframe)")
        
        # 1. Fetch Watchlist & High Priority Pairs
        watchlist = self.db.get_watchlist()
        core_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        
        # Combine and deduplicate
        scan_list = list(set(watchlist + core_pairs))
        print(f"Scanning {len(scan_list)} pairs: {scan_list}")
        
        # 2. Get CSM Context
        print("Calculating Currency Strength Matrix...")
        csm_text, _ = self.csm_service.get_currency_strength('1d')
        
        # 3. Scan (Multithreaded)
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {
                executor.submit(self.scanner.scan_symbol, symbol, '1d'): symbol 
                for symbol in scan_list
            }
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    print(f"Error scanning {symbol}: {e}")
                    
        # 4. Filter top setups
        print(f"Scan complete. Found {len(results)} potential setups.")
        
        # Sort by internal score if present, else just take top 3
        # Assuming the scanner returns a dict with a 'score'
        sorted_results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:3]
        
        if not sorted_results:
            self.send_webhook("Daily EOD Scan complete. No high-probability setups found today.", csm_text)
            return
            
        # 5. Build Webhook Payload (Discord Format preferred by default)
        message = "🚨 **End of Day Trading Setups (1D Chart)** 🚨\n\n"
        message += f"**Currency Strength Context:**\n```text\n{csm_text.split('Full Rankings')[0].strip()}\n```\n"
        
        for r in sorted_results:
            symbol = r.get('symbol', 'Unknown')
            signal = r.get('signal', 'Unknown')
            details = r.get('details', '')
            
            # Formatted block
            message += f"**{symbol}**\n"
            message += f"> Signal: {signal}\n"
            message += f"> Details: {details}\n"
            if symbol in watchlist:
                message += f"> *Found on Watchlist*\n"
            message += "\n"
            
        message += "\n*Please open pytrade UI for full AI analysis and position sizing.*"
        
        self.send_webhook(message)

    def send_webhook(self, content, csm_context=""):
        if not self.webhook_url:
            print("No WEBHOOK_URL found. Printing to console instead:")
            print("-" * 40)
            print(content)
            print("-" * 40)
            return
            
        try:
            # Basic Discord execution
            payload = {"content": content}
            if "telegram" in self.webhook_url.lower():
                 # Adapt for telegram if needed
                 payload = {"text": content} 
                 
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.webhook_url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print("Webhook sent successfully.")
        except Exception as e:
            print(f"Failed to send webhook: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run EOD Daily Scan and push to webhook")
    parser.add_argument("--dry-run", action="store_true", help="Run the scan but do not require webhook URL.")
    parser.add_argument("--webhook", type=str, help="Override Webhook URL (Discord or Telegram)")
    
    args = parser.parse_args()
    
    url = args.webhook if args.webhook else os.getenv("WEBHOOK_URL")
    if args.dry_run and not url:
        # Just mock a URL so it runs
        url = None 
        
    scanner = DailyEODScanner(webhook_url=url)
    scanner.run_scan()
