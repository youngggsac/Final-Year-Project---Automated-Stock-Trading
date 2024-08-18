import tkinter as tk
import random
from tkinter import ttk, messagebox, Menu
from PIL import Image, ImageTk
from database import create_user, validate_user, get_db_connection, update_stock_price, remove_trading_condition, remove_stock_from_trading_conditions, refresh_trading_condition_ids, get_notifications
from stock_updater import pause_updater
from trader import get_notifications

class TradingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Automated Stock Trading System")
        self.geometry("1200x800")
        self.configure(bg='#84A486')  # Main background color

        # Add logo
        self.logo = ImageTk.PhotoImage(Image.open("logo.png"))
        self.iconphoto(False, self.logo)

        self.current_user = None
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Define styles for buttons and labels
        self.style.configure('RoundedButton.TButton', font=('Helvetica', 12, 'bold'), padding=10, background='#2c5f2d', foreground='white', relief='flat', borderwidth=1)
        self.style.map('CustomButton.TButton',
                       relief=[('active', 'flat'), ('!active', 'solid')],
                       background=[('active', '#2c5f2d'), ('!active', '#84A486')],
                       foreground=[('active', 'white'), ('!active', '#2c5f2d')],
                       bordercolor=[('active', '#2c5f2d'), ('!active', '#E6E3DE')])
        self.style.configure('TLabel', font=('Helvetica', 12), background='#84A486', foreground='#2c5f2d')
        self.style.configure('TFrame', background='#84A486')
        self.style.configure('TNotebook', background='#84A486', borderwidth=0)
        self.style.configure('TNotebook.Tab', font=('Helvetica', 12, 'bold'), padding=[10, 10], background='#2c5f2d', foreground='white')
        self.style.map('TNotebook.Tab', background=[('selected', '#2c5f2d'), ('!selected', '#84A486')], foreground=[('selected', 'white'), ('!selected', 'white')])

        self.create_widgets()

    def create_widgets(self):
        # Navigation bar with user label
        self.nav_frame = ttk.Frame(self, style='TFrame', padding=10)
        self.nav_frame.pack(fill='x', padx=10, pady=10)
        self.nav_frame.pack_forget()  # Hide navigation bar initially

        self.user_label = ttk.Label(self.nav_frame, text="Welcome, User", font=('Helvetica', 14, 'bold'))
        self.user_label.pack(side='left', padx=10)

        # Add Logout Button
        self.logout_button = ttk.Button(self.nav_frame, text="Logout", command=self.logout, style='RoundedButton.TButton')
        self.logout_button.pack_forget()  # Initially hidden

        # Create a message box/inbox
        self.inbox_button = ttk.Button(self.nav_frame, text="Inbox", command=self.show_inbox, style='RoundedButton.TButton')
        self.inbox_button.pack_forget()  # Initially hidden

        # Notebook for different sections
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both', padx=20, pady=20)

        self.frames = {}
        for F in (LoginFrame, RegisterFrame):
            page_name = F.__name__
            frame = F(parent=self.notebook, controller=self)
            self.frames[page_name] = frame
            self.notebook.add(frame, text=page_name.replace('Frame', ''))
        
        self.show_frame("LoginFrame")
    
    def show_inbox(self):
        inbox_frame = ttk.Frame(self.notebook)
        self.notebook.add(inbox_frame, text="Inbox")
        self.notebook.select(inbox_frame)

        ttk.Label(inbox_frame, text="Inbox", font=('Helvetica', 16, 'bold')).pack(pady=10)

        self.inbox_tree = ttk.Treeview(inbox_frame, columns=('Message'), show='headings', height=15)
        self.inbox_tree.heading('Message', text='Message', anchor='center')
        self.inbox_tree.column('Message', anchor='center')
        self.inbox_tree.pack(padx=10, pady=10, expand=True, fill='both')

        self.load_inbox_messages()

    def load_inbox_messages(self):
        global notifications
        for notification in notifications:
            self.inbox_tree.insert('', 'end', values=(notification[1],))

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        self.notebook.select(frame)

    def login(self, username, password):
        if validate_user(username, password):
            self.current_user = username
            self.user_label.config(text=f"Welcome, {username}")
            self.show_logged_in_interface()
            self.hide_login_register_frames()
            self.frames["StocksFrame"].update_stocks()  # Start updating stocks immediately after login
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

    def logout(self):
        self.current_user = None
        self.hide_logged_in_interface()
        self.show_frame("LoginFrame")

    def hide_login_register_frames(self):
        self.notebook.forget(self.frames["LoginFrame"])
        self.notebook.forget(self.frames["RegisterFrame"])

    def show_logged_in_interface(self):
        # Show navigation bar
        self.nav_frame.pack(fill='x', padx=10, pady=10)
        self.logout_button.pack(side='right', padx=10)  # Pack the logout button
        self.inbox_button.pack(side='right', padx=10)  # Pack the inbox button

        # Add Stocks, Portfolio, and Conditions frames
        for F in (StocksFrame, PortfolioFrame, ConditionsFrame):
            page_name = F.__name__
            frame = F(parent=self.notebook, controller=self)
            self.frames[page_name] = frame
            self.notebook.add(frame, text=page_name.replace('Frame', ''))

        self.show_frame("StocksFrame")
        self.frames["PortfolioFrame"].update_portfolio()
        self.frames["ConditionsFrame"].update_conditions()
        self.frames["ConditionsFrame"].check_notifications()

    def hide_logged_in_interface(self):
        # Hide navigation bar
        self.nav_frame.pack_forget()
        self.logout_button.pack_forget()  # Hide the logout button
        self.inbox_button.pack_forget()  # Hide the inbox button

        # Remove Stocks, Portfolio, and Conditions frames
        for page_name in ("StocksFrame", "PortfolioFrame", "ConditionsFrame"):
            frame = self.frames.pop(page_name, None)
            if frame:
                self.notebook.forget(frame)

        self.show_frame("LoginFrame")

    def register(self, username, password, confirm_password):
        if password != confirm_password:
            messagebox.showerror("Registration Failed", "Passwords do not match")
            return
        
        if create_user(username, password):
            messagebox.showinfo("Registration Successful", "You can now log in with your new account")
            self.show_frame("LoginFrame")
        else:
            messagebox.showerror("Registration Failed", "Username already exists")

class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Automated Stock Trading System", font=('Helvetica', 18, 'bold')).pack(pady=60)
        ttk.Label(self, text="Username:", style='TLabel', font=('bold')).pack(pady=5)
        self.username_entry = ttk.Entry(self, width=30, font=('Helvetica', 12,))
        self.username_entry.pack(pady=10)
        ttk.Label(self, text="Password:", style='TLabel', font=('bold')).pack(pady=5)
        self.password_entry = ttk.Entry(self, show="*", width=30, font=('Helvetica', 12, 'bold'))
        self.password_entry.pack(pady=10)
        ttk.Button(self, text="Login", command=self.login, style='CustomButton.TButton').pack(pady=20)
        ttk.Button(self, text="Go to Register", command=lambda: self.controller.show_frame("RegisterFrame"), style='CustomButton.TButton').pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        self.controller.login(username, password)

class RegisterFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Create New Account", font=('Helvetica', 18, 'bold')).pack(pady=20)
        ttk.Label(self, text="Username:", style='TLabel').pack(pady=10)
        self.username_entry = ttk.Entry(self, width=30, font=('Helvetica', 12, 'bold'))
        self.username_entry.pack(pady=10)
        ttk.Label(self, text="Password:", style='TLabel').pack(pady=10)
        self.password_entry = ttk.Entry(self, show="*", width=30, font=('Helvetica', 12, 'bold'))
        self.password_entry.pack(pady=10)
        ttk.Label(self, text="Confirm Password:", style='TLabel').pack(pady=10)
        self.confirm_password_entry = ttk.Entry(self, show="*", width=30, font=('Helvetica', 12, 'bold'))
        self.confirm_password_entry.pack(pady=10)
        ttk.Button(self, text="Register", command=self.register, style='RoundedButton.TButton').pack(pady=20)
        ttk.Button(self, text="Back to Login", command=lambda: self.controller.show_frame("LoginFrame"), style='RoundedButton.TButton').pack()

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        self.controller.register(username, password, confirm_password)

class StocksFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Live Stock Prices", font=('Helvetica', 16, 'bold'), style='TLabel').pack(pady=10)
        
        # Define the columns for the Treeview
        self.stocks_tree = ttk.Treeview(self, columns=('Symbol', 'Name', 'Price', 'Change'), show='headings', height=15)
        
        # Set the heading for each column
        for col in self.stocks_tree["columns"]:
            self.stocks_tree.heading(col, text=col)

        self.stocks_tree.column('Symbol', anchor='center')
        self.stocks_tree.column('Name', anchor='center')
        self.stocks_tree.column('Price', anchor='center')
        self.stocks_tree.column('Change', anchor='center')
        
        # Pack the Treeview widget
        self.stocks_tree.pack(padx=10, pady=10, expand=True, fill='both')

        # Fetch and display the stocks
        self.load_stocks()

        # Add new widgets for manual stock price update
        stock_update_frame = ttk.Frame(self, padding="20", style='TFrame')
        stock_update_frame.pack(expand=True, fill='x', padx=20, pady=10)

        ttk.Label(stock_update_frame, text="Select Stock:", style='TLabel').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.stock_combobox = ttk.Combobox(stock_update_frame, state='readonly')
        self.stock_combobox.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(stock_update_frame, text="New Price:", style='TLabel').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.new_price_entry = ttk.Entry(stock_update_frame)
        self.new_price_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Button(stock_update_frame, text="Update Price", command=self.update_stock_price, style='RoundedButton.TButton').grid(row=2, column=0, columnspan=2, pady=20)

        self.load_stocks_for_update()
    
    def load_stocks(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT symbol, name, current_price FROM stocks')
        stocks = cursor.fetchall()
        for stock in stocks:
            symbol, name, price = stock
            self.stocks_tree.insert('', 'end', values=(symbol, name, f"${price:.2f}", "0.00"))
        conn.close()

    def load_stocks_for_update(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT symbol FROM stocks')
        stocks = cursor.fetchall()
        self.stock_combobox['values'] = [stock[0] for stock in stocks]
        conn.close()

    def update_stock_price(self):
        global pause_updater
        selected_stock = self.stock_combobox.get()
        new_price = self.new_price_entry.get()
        if not selected_stock or not new_price:
            messagebox.showwarning("Input Error", "Please select a stock and enter a new price.")
            return
        try:
            new_price = float(new_price)
            update_stock_price(selected_stock, new_price)
            print(f"Updated {selected_stock} to new price {new_price}")
            messagebox.showinfo("Success", f"Price for {selected_stock} updated to ${new_price:.2f}")
            self.update_stocks()
            # Pause the updater for 30 seconds
            pause_updater = True
            self.after(30000, self.resume_updater)
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid price.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def resume_updater(self):
        global pause_updater
        pause_updater = False

    def update_stocks(self):
        if not self.controller.current_user:
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT symbol, name, current_price FROM stocks')
        stocks = cursor.fetchall()
        self.stocks_tree.delete(*self.stocks_tree.get_children())
        for stock in stocks:
            symbol, name, current_price = stock
            
            # Apply a random change to the current price
            change = random.uniform(-0.5, 0.5) * current_price
            new_price = current_price + change
            update_stock_price(symbol, new_price)  # Update the database with the new price
            
            if change > 0:
                tag = 'positive'
            elif change < 0:
                tag = 'negative'
            else:
                tag = 'neutral'
            self.stocks_tree.insert('', 'end', values=(symbol, name, f"${current_price:.2f}", f"{change:+.2f}"), tags=(tag,))
        conn.close()

        # Apply tag styles
        self.stocks_tree.tag_configure('positive', background='lightgreen')
        self.stocks_tree.tag_configure('negative', background='lightcoral')
        self.stocks_tree.tag_configure('neutral', background='lightblue')

        self.after(300000, self.update_stocks)  # Update every 300,000 ms or 5 minutes

class PortfolioFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="My Portfolio", font=('Helvetica', 16, 'bold'), style='TLabel').pack(pady=10)
        self.portfolio_tree = ttk.Treeview(self, columns=('Symbol', 'Quantity', 'Avg Price', 'Current Price', 'Profit/Loss'), show='headings', height=10,)
        for col in self.portfolio_tree["columns"]:
            self.portfolio_tree.heading(col, text=col)
            self.portfolio_tree.column(col, anchor='center')
        self.portfolio_tree.pack(padx=10, pady=10, expand=True, fill='both')
        self.notification_label = ttk.Label(self, text="", font=('Helvetica', 12, 'bold'), style='TLabel')
        self.notification_label.pack(pady=10)

    def update_portfolio(self):
        if not self.controller.current_user:
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.symbol, us.quantity, us.purchase_price, s.current_price
            FROM user_stocks us
            JOIN stocks s ON us.stock_id = s.id
            JOIN users u ON us.user_id = u.id
            WHERE u.username = ?
        ''', (self.controller.current_user,))
        portfolio = cursor.fetchall()
        self.portfolio_tree.delete(*self.portfolio_tree.get_children())
        for stock in portfolio:
            symbol, quantity, avg_price, current_price = stock
            profit_loss = (current_price - avg_price) * quantity
            self.portfolio_tree.insert('', 'end', values=(symbol, quantity, f"${avg_price:.2f}", f"${current_price:.2f}", f"${profit_loss:.2f}"))
        print(f"Updated portfolio: {portfolio}")  # Debug statement
        conn.close()
        self.after(5000, self.update_portfolio)  # Update every 5 seconds


class ConditionsFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, padding="20")
        self.controller = controller
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Set Trading Conditions", font=('Helvetica', 16, 'bold'), style='TLabel').pack(pady=10)

        conditions_frame = ttk.Frame(self, style='TFrame')
        conditions_frame.pack(expand=True, fill='both')
        
        self.conditions_tree = ttk.Treeview(conditions_frame, columns=("ID", "Stock", "Type", "Target Price", "Quantity"), show='headings')
        for col in self.conditions_tree["columns"]:
            self.conditions_tree.heading(col, text=col)
            self.conditions_tree.column(col, anchor='center')
        self.conditions_tree.pack(expand=True, fill='both', padx=20, pady=10)

        condition_frame = ttk.Frame(self, padding="20", style='TFrame')
        condition_frame.pack(expand=True, fill='x', padx=20, pady=10)

        ttk.Label(condition_frame, text="Select Stock:", style='TLabel').grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.condition_stock_combobox = ttk.Combobox(condition_frame, state='readonly')
        self.condition_stock_combobox.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(condition_frame, text="Condition Type:", style='TLabel').grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.condition_type_combobox = ttk.Combobox(condition_frame, values=["Buy", "Sell"], state='readonly')
        self.condition_type_combobox.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(condition_frame, text="Target Price:", style='TLabel').grid(row=2, column=0, padx=10, pady=10, sticky='e')
        self.condition_target_price_entry = ttk.Entry(condition_frame)
        self.condition_target_price_entry.grid(row=2, column=1, padx=10, pady=10)

        ttk.Label(condition_frame, text="Quantity:", style='TLabel').grid(row=3, column=0, padx=10, pady=10, sticky='e')
        self.condition_quantity_entry = ttk.Entry(condition_frame)
        self.condition_quantity_entry.grid(row=3, column=1, padx=10, pady=10)

        
        ttk.Button(condition_frame, text="Set Condition", command=self.set_condition, style='RoundedButton.TButton').grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(condition_frame, text="Remove Selected Stock", command=self.remove_selected_stock, style='RoundedButton.TButton').grid(row=5, column=0, columnspan=2, pady=10)

        self.load_stocks_for_conditions()
        self.update_conditions()

    def load_stocks_for_conditions(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT symbol FROM stocks')
        stocks = cursor.fetchall()
        self.condition_stock_combobox['values'] = [stock[0] for stock in stocks]
        conn.close()

    def set_condition(self):
        if not self.controller.current_user:
            messagebox.showerror("Error", "Please log in first")
            return

        stock = self.condition_stock_combobox.get()
        condition_type = self.condition_type_combobox.get()
        try:
            target_price = float(self.condition_target_price_entry.get())
            quantity = int(self.condition_quantity_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid target price or quantity")
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM stocks WHERE symbol = ?', (stock,))
        stock_id = cursor.fetchone()

        stock_id = stock_id[0]  

        if not stock_id:
            messagebox.showerror("Error", "Invalid stock symbol")
            conn.close()
            return

        cursor.execute('SELECT id FROM users WHERE username = ?', (self.controller.current_user,))
        user_id = cursor.fetchone()[0]

        if condition_type.lower() == 'sell':
            cursor.execute('SELECT quantity FROM user_stocks WHERE user_id = ? AND stock_id = ?', (user_id, stock_id[0]))
            user_stock = cursor.fetchone()
            if not user_stock or user_stock[0] < quantity:
                messagebox.showerror("Error", "You do not own enough of this stock to sell.")
                conn.close()
                return

        cursor.execute('''
            INSERT INTO trading_conditions (user_id, stock_id, condition_type, target_price, quantity)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.controller.current_user, stock_id, condition_type, target_price, quantity))
        

        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Trading condition set successfully")
        self.update_conditions()


    def remove_selected_stock(self):
        selected_item = self.conditions_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a stock to remove.")
            return

        stock_symbol = self.conditions_tree.item(selected_item, "values")[1]

        try:
            remove_stock_from_trading_conditions(stock_symbol)
            messagebox.showinfo("Success", f"Stock {stock_symbol} removed successfully.")
            self.update_conditions()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_conditions(self):
        if not self.controller.current_user:
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tc.id, s.symbol, tc.condition_type, tc.target_price
            FROM trading_conditions tc
            JOIN stocks s ON tc.stock_id = s.id
            JOIN users u ON tc.user_id = u.id
            WHERE u.username = ?
        ''', (self.controller.current_user,))
        
        conditions = cursor.fetchall()
        
        self.conditions_tree.delete(*self.conditions_tree.get_children())
        for condition in conditions:
            self.conditions_tree.insert('', 'end', values=condition)
        
        conn.close()
        self.after(5000, self.update_conditions)  # Update every 5 seconds

    def check_notifications(self):
        notifications = get_notifications()
        for username, message in notifications:
            if username == self.controller.current_user:
                self.controller.frames["PortfolioFrame"].notification_label.config(text=message)
                messagebox.showinfo("Trade Executed", message)
                self.controller.frames["PortfolioFrame"].update_portfolio()  # Update portfolio immediately after a trade
        
        self.after(1000, self.check_notifications)  # Check every second


if __name__ == "__main__":
    app = TradingApp()
    app.run()