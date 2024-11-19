import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message

app = Flask(__name__)

DATABASE = 'offline_wallet.db'  # Name of your SQLite database file

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)  # Set timeout to avoid locking issues
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                         (username, email, password))
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.close()
            if 'UNIQUE constraint failed: users.username' in str(e):
                return "Username already exists. Please try another one."
            elif 'UNIQUE constraint failed: users.email' in str(e):
                return "Email already exists. Please try another one."
            return "Registration failed."
        conn.close()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Get 'username' from the form
        password = request.form.get('password')  # Get 'password' from the form

        # Ensure both fields are provided
        if not username or not password:
            error_message = "Both username and password are required!"
            return render_template('login.html', error=error_message)

        # Query the database for the user
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            # Redirect to the dashboard if login is successful
            return redirect(url_for('dashboard', username=username))
        else:
            # Invalid credentials
            error_message = "Invalid username or password!"
            return render_template('login.html', error=error_message)

    return render_template('login.html')


@app.route('/dashboard/<username>')
def dashboard(username):
    # Connect to the database
    conn = get_db_connection()
    
    # Fetch the user's data based on the username
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    
    conn.close()

    if user:
        # Render the dashboard page with user data (including balance)
        return render_template('dashboard.html', user=user)
    else:
        # Redirect to home if the user does not exist
        return redirect(url_for('home'))


@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        sender_username = request.form['sender']
        recipient_username = request.form['recipient']
        amount = float(request.form['amount'])

        conn = get_db_connection()
        sender = conn.execute('SELECT * FROM users WHERE username = ?', (sender_username,)).fetchone()
        recipient = conn.execute('SELECT * FROM users WHERE username = ?', (recipient_username,)).fetchone()

        if sender and recipient and sender['balance'] >= amount:
            # Update balances and log the transaction
            conn.execute('UPDATE users SET balance = balance - ? WHERE username = ?', (amount, sender_username))
            conn.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, recipient_username))
            conn.execute('INSERT INTO transactions (sender_id, recipient_id, amount) VALUES (?, ?, ?)',
                         (sender['id'], recipient['id'], amount))
            conn.commit()
            conn.close()

            # Redirect to confirmation page
            return redirect(url_for('confirmation', recipient=recipient_username, amount=amount, sender=sender_username))

        else:
            conn.close()
            return "Transfer failed. Check balance or recipient username."

    return render_template('transfer.html')



@app.route('/confirmation')
def confirmation():
    recipient = request.args.get('recipient')
    amount = request.args.get('amount')
    sender = request.args.get('sender')

    if not recipient or not amount or not sender:
        return "Error: Missing data for transfer confirmation."

    # Render the confirmation page
    return render_template('confirmation.html', recipient=recipient, amount=amount, sender=sender)




if __name__ == '__main__':
    app.run(debug=True)
