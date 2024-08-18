import sqlite3
import bcrypt
from queue import Queue

# Global notification queue
notification_queue = Queue()

def get_db_connection():
    return sqlite3.connect('stock_trading.db')

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    #cursor.execute('DROP TABLE IF EXISTS users')
    #cursor.execute('DROP TABLE IF EXISTS stocks')
    #cursor.execute('DROP TABLE IF EXISTS user_stocks')
    #cursor.execute('DROP TABLE IF EXISTS trading_conditions')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            current_price REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stocks (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            stock_id INTEGER,
            quantity INTEGER,
            purchase_price REAL,
            UNIQUE(user_id, stock_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (stock_id) REFERENCES stocks (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_conditions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            stock_id INTEGER,
            condition_type TEXT,
            target_price REAL,
            quantity INTEGER, 
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (stock_id) REFERENCES stocks (id)
        )
    ''')

    # Insert some initial stocks
    stocks = [
        ('GOOGL', 'Alphabet Inc.', 2800.0),
        ('AMZN', 'Amazon.com Inc.', 5200.0),
        ('AAPL', 'Apple Inc.', 150.0),
        ('NOK', 'China Mobile (Hong Kong) Ltd.', 4300.0),
        ('CSCO', 'Cisco Systems Inc.', 900.0),
        ('KO', 'Coca-Cola Company (The)', 1650.0),
        ('DNA', 'Genentech, Inc.', 600.0),
        ('INTC', 'Intel Corporation', 400.0),
        ('IBM', 'International Business Machines Corporation', 9300.0),
        ('JNJ', 'JOHNSON & JOHNSON', 3300.0),
        ('MSFT', 'Microsoft Corporation', 300.0),
        ('MTU', 'Mitsubishi UFJ Financial Group Inc.', 3300.0),
        ('NFLX', 'Netflix', 3300.0),
        ('RDS/B', 'ROYAL DUTCH SHELL PLC', 7000.0),
        ('NOK', 'Nokia Corporation', 1700.0),
        ('TWX', 'Time Warner Inc.', 5200.0),
        ('TM', 'Toyota Motor Corporation', 3700.0),
        ('VOD', 'Vodafone AirTouch Public Limited Company', 3300.0),
        ('WMT', 'Wal-Mart Stores, Inc.', 3300.0),
    ]
    
    cursor.executemany('INSERT OR IGNORE INTO stocks (symbol, name, current_price) VALUES (?, ?, ?)', stocks)
    
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def validate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    
    if result:
        hashed_password = result[0]
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return True
    
    return False

def update_stock_price(symbol, new_price):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE stocks SET current_price = ? WHERE symbol = ?', (new_price, symbol))
    conn.commit()
    conn.close()

def remove_trading_condition(condition_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM trading_conditions WHERE id = ?', (condition_id,))
    conn.commit()
    conn.close()

def remove_stock_from_trading_conditions(stock_symbol):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM trading_conditions 
        WHERE stock_id = (SELECT id FROM stocks WHERE symbol = ?)
    ''', (stock_symbol,))
    conn.commit()
    conn.close()

def refresh_trading_condition_ids():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Select all remaining conditions ordered by the current ID
    cursor.execute('SELECT id FROM trading_conditions ORDER BY id')
    conditions = cursor.fetchall()

    # Reassign IDs sequentially starting from 1
    new_id = 1
    for condition in conditions:
        old_id = condition[0]
        cursor.execute('UPDATE trading_conditions SET id = ? WHERE id = ?', (new_id, old_id))
        new_id += 1

    conn.commit()
    conn.close()

def set_trading_condition(user_id, stock_id, condition_type, target_price, quantity):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO trading_conditions (user_id, stock_id, condition_type, target_price, quantity) VALUES (?, ?, ?, ?, ?)', (user_id, stock_id, condition_type, target_price, quantity))
        conn.commit()
        print(f"Condition set: {condition_type} {quantity} shares at {target_price} for stock ID {stock_id}")  # Debug statement
        
        # Fetch all conditions to verify
        cursor.execute('SELECT * FROM trading_conditions WHERE user_id = ?', (user_id,))
        conditions = cursor.fetchall()
        print(f"Current trading conditions for user {user_id}: {conditions}")
    except sqlite3.Error as e:
        print(f"Error inserting trading condition: {e}")
    finally:
        conn.close()

def get_notifications():
    notifications = []
    while not notification_queue.empty():
        notifications.append(notification_queue.get())
    return notifications

def add_quantity_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE trading_conditions ADD COLUMN quantity INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

if __name__ == '__main__':
    initialize_database()
    add_quantity_column()
