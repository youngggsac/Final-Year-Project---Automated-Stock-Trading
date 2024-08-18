import time
import random
import threading
from database import get_db_connection

pause_updater = False

def update_stock_prices():
    global pause_updater
    conn = get_db_connection()
    cursor = conn.cursor()
    
    while True:
        if not pause_updater:
            cursor.execute('SELECT id, current_price FROM stocks')
            stocks = cursor.fetchall()
        
            for stock_id, current_price in stocks:
                # Simulate price change
                change_percent = random.uniform(-0.5, 0.5)  # -5% to 2% change
                new_price = current_price * (1 + change_percent)
                new_price = round(new_price, 2)
                
                cursor.execute('UPDATE stocks SET current_price = ? WHERE id = ?', (new_price, stock_id))
            
            conn.commit()
        time.sleep(5)  # Update every 5 seconds

def start_stock_updater():
    thread = threading.Thread(target=update_stock_prices)
    thread.daemon = True
    thread.start()
