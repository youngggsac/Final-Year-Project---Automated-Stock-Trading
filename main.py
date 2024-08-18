import tkinter as tk
from gui import TradingApp
from database import initialize_database
from stock_updater import start_stock_updater
from trader import start_trader

if __name__ == "__main__":
    initialize_database()
    start_stock_updater()
    start_trader()
    
    app = TradingApp()
    app.mainloop()