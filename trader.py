import time
import threading
import logging
import tkinter as tk
from database import get_db_connection
from queue import Queue
from tkinter import messagebox

# Global notification queue
notification_queue = Queue()
notifications = []
shown_notifications = set()  # Use a set for faster lookup and uniqueness

def check_trading_conditions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    while True:
        cursor.execute('''
            SELECT tc.id, tc.user_id, tc.stock_id, tc.condition_type, tc.target_price, tc.quantity, s.current_price, s.symbol, u.username
            FROM trading_conditions tc
            JOIN stocks s ON tc.stock_id = s.id
            JOIN users u ON tc.user_id = u.id
        ''')
        conditions = cursor.fetchall()
        
        for condition in conditions:
            condition_id, user_id, stock_id, condition_type, target_price, quantity, current_price, symbol, username = condition
            print(f"Checking condition for {symbol}: {condition_type} at {target_price}, current price is {current_price}")  # Debug statement
            
            if (condition_type == 'Buy' and current_price <= target_price) or \
               (condition_type == 'Sell' and current_price >= target_price):
                # Execute trade
                execute_trade(user_id, stock_id, condition_type, current_price, symbol, username, quantity)
                print(f"Condition met for {symbol}: Executing {condition_type} at {current_price}")  # Debug statement
                
                # Remove the condition after trade execution
                try:
                    cursor.execute('DELETE FROM trading_conditions WHERE id = ?', (condition_id,))
                    conn.commit()
                    logging.info(f"Successfully deleted condition ID {condition_id} for {symbol}")
                except Exception as e:
                    logging.error(f"Failed to delete condition ID {condition_id} for {symbol}: {str(e)}")
        
        time.sleep(1)  # Check every second

def execute_trade(user_id, stock_id, trade_type, price, symbol, username, quantity):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if trade_type.lower() == 'buy':
        cursor.execute('''
            INSERT INTO user_stocks (user_id, stock_id, quantity, purchase_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, stock_id) DO UPDATE SET
            quantity = quantity + ?,
            purchase_price = (purchase_price * (quantity - ?) + ?) / (quantity + ?)
        ''', (user_id, stock_id, quantity, price, quantity, quantity, price, quantity))
        message = f"Bought {quantity} shares of {symbol} at ${price:.2f}"
    elif trade_type.lower() == 'sell':
        cursor.execute('''
            UPDATE user_stocks
            SET quantity = quantity - ?
            WHERE user_id = ? AND stock_id = ? AND quantity >= ?
        ''', (quantity, user_id, stock_id, quantity))
        
        # Remove the stock from user_stocks if quantity becomes 0
        cursor.execute('''
            DELETE FROM user_stocks
            WHERE user_id = ? AND stock_id = ? AND quantity = 0
        ''', (user_id, stock_id))
        message = f"Sold {quantity} shares of {symbol} at ${price:.2f}"
    
    conn.commit()
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM trading_conditions WHERE stock_id = ? AND user_id = ?', (stock_id, user_id))
    conn.commit()
    conn.close()
    
    # Add notification to list and show message box
    if (username, message) not in shown_notifications:
        shown_notifications.add((username, message))  # Track shown notifications
        root = tk.Tk()
        root.withdraw()  # Prevent root window from appearing
        messagebox.showinfo("Trade Executed", message)
        root.destroy()

    # Update portfolio frame
    from gui import app
    app.frames["PortfolioFrame"].update_portfolio()

def start_trader():
    thread = threading.Thread(target=check_trading_conditions)
    thread.daemon = True
    thread.start()

def get_notifications():
    global notifications
    return notifications
