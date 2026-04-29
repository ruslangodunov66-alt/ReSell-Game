def set_temp_product(user_id, product):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO temp_products (user_id, product) VALUES (?, ?)', (user_id, product))
    conn.commit()
    conn.close()

def get_temp_product(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT product FROM temp_products WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def generate_random_buyer(product):
    buyers = [("Маркет", 0.8, 1), ("Перекуп", 1.2, 3), ("Оптовик", 1.5, 5), ("Коллекционер", 0.9, 4), ("Трейдер", 1.1, 2)]
    name, mult, req = random.choice(buyers)
    # находим рыночную цену
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT current_price FROM market WHERE product = ?', (product,))
    row = cur.fetchone()
    conn.close()
    market_price = row[0] if row else 100
    price = int(market_price * mult)
    return price, req, name

def save_offer(user_id, product, price):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO offers (user_id, product, price) VALUES (?, ?, ?)', (user_id, product, price))
    conn.commit()
    conn.close()

def get_offer(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT product, price FROM offers WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row if row else None

def clear_offer(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM offers WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()