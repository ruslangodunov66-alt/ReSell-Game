import sqlite3
from datetime import datetime, timedelta
import random

DB_NAME = "trade_game.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 1000,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            sell_skill INTEGER DEFAULT 1,
            buy_skill INTEGER DEFAULT 1,
            prod_category TEXT DEFAULT 'electronics',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    # Таблица рыночных предложений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            base_price INTEGER,
            demand TEXT,
            current_price INTEGER,
            expires_at TIMESTAMP
        )
    ''')
    # Таблица достижений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            name TEXT,
            earned_at TIMESTAMP,
            PRIMARY KEY (user_id, name)
        )
    ''')
    conn.commit()
    conn.close()
    generate_market()

def register_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not cur.fetchone():
        cur.execute('''
            INSERT INTO users (user_id, username, balance, level, exp, sell_skill, buy_skill, prod_category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, 1000, 1, 0, 1, 1, 'electronics', datetime.now()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT balance, level, exp, sell_skill, buy_skill, prod_category, wins, losses FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {'balance': row[0], 'level': row[1], 'exp': row[2],
                'sell_skill': row[3], 'buy_skill': row[4], 'prod_category': row[5],
                'wins': row[6], 'losses': row[7]}
    return None

def update_user(user_id, balance=None, exp=None, sell_skill=None, buy_skill=None, wins=None, losses=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fields = []
    params = []
    if balance is not None:
        fields.append("balance = ?")
        params.append(balance)
    if exp is not None:
        fields.append("exp = ?")
        params.append(exp)
    if sell_skill is not None:
        fields.append("sell_skill = ?")
        params.append(sell_skill)
    if buy_skill is not None:
        fields.append("buy_skill = ?")
        params.append(buy_skill)
    if wins is not None:
        fields.append("wins = ?")
        params.append(wins)
    if losses is not None:
        fields.append("losses = ?")
        params.append(losses)
    if fields:
        params.append(user_id)
        cur.execute(f'UPDATE users SET {", ".join(fields)} WHERE user_id = ?', params)
    conn.commit()
    conn.close()

def add_exp(user_id, amount):
    user = get_user(user_id)
    if not user:
        return None
    new_exp = user['exp'] + amount
    exp_needed = user['level'] * 100
    if new_exp >= exp_needed:
        new_level = user['level'] + 1
        new_exp -= exp_needed
        update_user(user_id, exp=new_exp)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('UPDATE users SET level = ? WHERE user_id = ?', (new_level, user_id))
        conn.commit()
        conn.close()
        return new_level
    else:
        update_user(user_id, exp=new_exp)
        return None

def generate_market():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    products = [
        ('Смартфон', 500),
        ('Ноутбук', 800),
        ('Наушники', 150),
        ('Кроссовки', 200),
        ('Футболка', 80),
        ('Пылесос', 300)
    ]
    demand_levels = ['низкий', 'средний', 'высокий']
    cur.execute('DELETE FROM market')
    for product, base in products:
        demand = random.choice(demand_levels)
        multiplier = {'низкий': 0.8, 'средний': 1.0, 'высокий': 1.3}[demand]
        current_price = int(base * multiplier)
        expires_at = datetime.now() + timedelta(hours=random.randint(6, 24))
        cur.execute('''
            INSERT INTO market (product, base_price, demand, current_price, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (product, base, demand, current_price, expires_at))
    conn.commit()
    conn.close()

def get_market_offers():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT id, product, demand, current_price, expires_at FROM market ORDER BY current_price ASC')
    rows = cur.fetchall()
    conn.close()
    return [{'id': r[0], 'product': r[1], 'demand': r[2], 'price': r[3], 'expires_at': r[4]} for r in rows]

def earn_achievement(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO achievements (user_id, name, earned_at) VALUES (?, ?, ?)', (user_id, name, datetime.now()))
    conn.commit()
    conn.close()