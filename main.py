import customtkinter as ctk
from ui.main_window import MainWindow
from controllers.main_controller import MainController
from services.market_data import MarketDataProvider
from services.ai_service import AITrader
from services.news_service import NewsService
from services.chart_service import ChartService
from services.macro_service import MacroService
from services.cot_service import COTService
from services.logger import Logger

def main():
    # 1. Initialize Logger
    logger = Logger()
    logger.info("Application Starting...")

    try:
        # 2. Initialize Services (Dependency Injection Container)
        services = {
            'market': MarketDataProvider(),
            'ai': AITrader(),
            'news': NewsService(),
            'chart': ChartService(),
            'macro': MacroService(),
            'cot': COTService()
        }

        # 3. Initialize View
        app = MainWindow()

        # 4. Initialize Controller with View and Services
        controller = MainController(app, services)
        
        # 5. Link Controller to View
        app.set_controller(controller)

        # 6. Run
        app.mainloop()

    except Exception as e:
        logger.exception(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
