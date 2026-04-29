import sqlite3
from datetime import datetime, timedelta
import random

DB_NAME = "trade_game.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Включение WAL для производительности
    cur.execute('PRAGMA journal_mode=WAL;')
    cur.execute('PRAGMA cache_size=-20000;')

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
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            last_play TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP
        )
    ''')
    # Инвентарь пользователя
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            product TEXT,
            quantity INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, product)
        )
    ''')
    # Товары на рынке
    cur.execute('''
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            brand TEXT,
            base_price INTEGER,
            current_price INTEGER,
            season TEXT,
            demand INTEGER DEFAULT 50,
            expires_at TIMESTAMP
        )
    ''')
    # Поставщики
    cur.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rating INTEGER,
            discount INTEGER,
            risk INTEGER
        )
    ''')
    # Клиенты (предложения)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            user_id INTEGER PRIMARY KEY,
            customer_name TEXT,
            product TEXT,
            price INTEGER,
            expires_at TIMESTAMP
        )
    ''')
    # Достижения
    cur.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            name TEXT,
            earned_at TIMESTAMP,
            PRIMARY KEY (user_id, name)
        )
    ''')

    # Заполняем поставщиков, если пусто
    cur.execute('SELECT COUNT(*) FROM suppliers')
    if cur.fetchone()[0] == 0:
        suppliers = [
            ("Маркет-Импорт", 5, 15, 30),   # высокий риск, большая скидка
            ("Мега-Сток", 8, 8, 15),
            ("Китай-Трейд", 3, 25, 50),      # низкий рейтинг, большая скидка, высокий риск
            ("Евро-Логистик", 9, 5, 10),
            ("Альфа-Опт", 7, 10, 15),
            ("Супер-Вэй", 2, 30, 60)         # очень низкий рейтинг
        ]
        for name, rating, discount, risk in suppliers:
            cur.execute('INSERT INTO suppliers (name, rating, discount, risk) VALUES (?, ?, ?, ?)', (name, rating, discount, risk))

    conn.commit()
    conn.close()

def register_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not cur.fetchone():
        cur.execute('''
            INSERT INTO users (user_id, username, balance, level, exp, sell_skill, buy_skill, referrals, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, 1000, 1, 0, 1, 1, 0, datetime.now()))
        # Выдаём стартовый инвентарь (10 случайных товаров)
        products = generate_products()
        chosen = random.sample(products, min(10, len(products)))
        for prod, brand, price, season in chosen:
            cur.execute('INSERT INTO inventory (user_id, product, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product) DO UPDATE SET quantity = quantity + 1', (user_id, f"{brand} {prod}", 1))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT balance, level, exp, sell_skill, buy_skill, wins, losses, referrals FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {'balance': row[0], 'level': row[1], 'exp': row[2], 'sell_skill': row[3], 'buy_skill': row[4], 'wins': row[5], 'losses': row[6], 'referrals': row[7]}
    return None

def update_user(user_id, balance=None, sell_skill=None, buy_skill=None, exp=None, wins=None, losses=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    fields = []
    params = []
    if balance is not None:
        fields.append("balance = ?")
        params.append(balance)
    if sell_skill is not None:
        fields.append("sell_skill = ?")
        params.append(sell_skill)
    if buy_skill is not None:
        fields.append("buy_skill = ?")
        params.append(buy_skill)
    if exp is not None:
        fields.append("exp = ?")
        params.append(exp)
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

def generate_products():
    """Генерирует товары с брендами и сезонами"""
    seasons = ["весна", "лето", "осень", "зима", "всесезон"]
    data = []
    # Куртки
    brands_coats = ["Canada Goose", "The North Face", "Moncler", "Patagonia", "Columbia", "Fjällräven", "Helly Hansen", "Marmot"]
    for brand in brands_coats:
        data.append((f"{brand} пуховик", brand, random.randint(8000, 30000), random.choice(["осень", "зима"])))
        data.append((f"{brand} ветровка", brand, random.randint(3000, 12000), random.choice(["весна", "лето", "осень"])))
    # Электроника
    brands_elec = ["Apple", "Samsung", "Sony", "Xiaomi", "Huawei", "OnePlus", "LG", "Bose"]
    for brand in brands_elec:
        data.append((f"{brand} наушники", brand, random.randint(2000, 15000), "всесезон"))
        data.append((f"{brand} смартфон", brand, random.randint(15000, 80000), "всесезон"))
        data.append((f"{brand} часы", brand, random.randint(5000, 25000), "всесезон"))
    # Отдельно часы (люксовые)
    brands_watch = ["Rolex", "Omega", "Casio", "Seiko", "Tissot", "Citizen", "G-Shock", "Apple"]
    for brand in brands_watch:
        data.append((f"{brand} часы", brand, random.randint(3000, 150000), "всесезон"))
    # Одежда (вещи)
    brands_cloth = ["Nike", "Adidas", "Puma", "Reebok", "Under Armour", "Zara", "H&M", "Uniqlo"]
    for brand in brands_cloth:
        data.append((f"{brand} футболка", brand, random.randint(1500, 6000), "лето"))
        data.append((f"{brand} джинсы", brand, random.randint(2000, 10000), "всесезон"))
        data.append((f"{brand} кроссовки", brand, random.randint(3000, 18000), random.choice(["весна", "лето", "осень"])))
    return data

def generate_market():
    """Создаёт рыночные предложения от поставщиков"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM market')
    products = generate_products()
    suppliers = cur.execute('SELECT id, name, rating, discount, risk FROM suppliers').fetchall()
    for prod, brand, price, season in random.sample(products, min(50, len(products))):
        supplier = random.choice(suppliers)
        sup_id, sup_name, rating, discount, risk = supplier
        # Цена зависит от рейтинга поставщика: чем ниже рейтинг, тем дешевле
        final_price = int(price * (1 - discount / 100))
        final_price = max(final_price, 200)  # не ниже 200
        expires_at = datetime.now() + timedelta(hours=random.randint(2, 12))
        cur.execute('''
            INSERT INTO market (product, brand, base_price, current_price, season, demand, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (prod, brand, price, final_price, season, random.randint(20, 100), expires_at))
    conn.commit()
    conn.close()

def get_market_offers(user_id):
    """Возвращает рыночные предложения (от поставщиков)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    user = get_user(user_id)
    buy_skill = user['buy_skill'] if user else 1
    # Скидка от навыка закупок
    skill_discount = min(buy_skill * 0.02, 0.3)  # до 30% скидки
    cur.execute('SELECT id, product, brand, current_price, season, expires_at FROM market ORDER BY current_price ASC')
    rows = cur.fetchall()
    offers = []
    for r in rows:
        price = int(r[3] * (1 - skill_discount))
        offers.append({'id': r[0], 'product': f"{r[2]} {r[1]}", 'price': price, 'season': r[4], 'expires_at': r[5]})
    conn.close()
    return offers

def buy_product(user_id, product_full, quantity):
    """Покупка товара у поставщика"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Находим предложение
    cur.execute('SELECT id, current_price FROM market WHERE product = ?', (product_full.split(' ', 1)[1],))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Товар не найден"
    price = row[1]
    user = get_user(user_id)
    skill_discount = min(user['buy_skill'] * 0.02, 0.3)
    final_price = int(price * (1 - skill_discount)) * quantity
    if user['balance'] < final_price:
        return False, f"Не хватает {final_price} 💎"
    # Списываем деньги
    update_user(user_id, balance=user['balance'] - final_price)
    # Добавляем в инвентарь
    cur.execute('INSERT INTO inventory (user_id, product, quantity) VALUES (?, ?, ?) ON CONFLICT(user_id, product) DO UPDATE SET quantity = quantity + ?', (user_id, product_full, quantity, quantity))
    conn.commit()
    conn.close()
    return True, f"✅ Куплено {product_full} x{quantity} за {final_price} 💎"

def get_inventory(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT product, quantity FROM inventory WHERE user_id = ?', (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{'product': r[0], 'quantity': r[1]} for r in rows]

def remove_from_inventory(user_id, product):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT quantity FROM inventory WHERE user_id = ? AND product = ?', (user_id, product))
    row = cur.fetchone()
    if not row or row[0] < 1:
        conn.close()
        return False
    new_qty = row[0] - 1
    if new_qty == 0:
        cur.execute('DELETE FROM inventory WHERE user_id = ? AND product = ?', (user_id, product))
    else:
        cur.execute('UPDATE inventory SET quantity = ? WHERE user_id = ? AND product = ?', (new_qty, user_id, product))
    conn.commit()
    conn.close()
    return True

def get_random_customer():
    customers = ["Анна", "Михаил", "Екатерина", "Дмитрий", "Ольга", "Сергей", "Татьяна", "Алексей", "Наталья", "Владимир", "Ирина", "Константин"]
    return random.choice(customers)

def generate_customer_offer(user_id, product):
    """Генерирует предложение от случайного клиента"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Базовая цена товара
    cur.execute('SELECT product, brand, current_price FROM market WHERE product = ?', (product.split(' ', 1)[1],))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    base_price = row[2]
    user = get_user(user_id)
    skill_multiplier = 1 + user['sell_skill'] * 0.05
    # Случайный разброс цены (0.7 до 1.3)
    random_factor = random.uniform(0.7, 1.3)
    offer_price = int(base_price * skill_multiplier * random_factor)
    offer_price = max(offer_price, 100)
    customer = get_random_customer()
    expires_at = datetime.now() + timedelta(minutes=random.randint(10, 60))
    cur.execute('INSERT OR REPLACE INTO offers (user_id, customer_name, product, price, expires_at) VALUES (?, ?, ?, ?, ?)', (user_id, customer, product, offer_price, expires_at))
    conn.commit()
    conn.close()
    return {'customer': customer, 'price': offer_price, 'expires_at': expires_at}

def get_offer(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT customer_name, product, price, expires_at FROM offers WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    if row and datetime.now() < datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S.%f"):
        return {'customer': row[0], 'product': row[1], 'price': row[2], 'expires_at': row[3]}
    return None

def clear_offer(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM offers WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def earn_achievement(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO achievements (user_id, name, earned_at) VALUES (?, ?, ?)', (user_id, name, datetime.now()))
    conn.commit()
    conn.close()