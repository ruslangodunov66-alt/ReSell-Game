import random
import hashlib
import json
import os
import asyncio
import re
import time as time_module
from collections import defaultdict
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram import F
from openai import OpenAI

# ==================== КОНФИГ ====================
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'
CHANNEL_LINK = '@vintagedrop61'
BOT_USERNAME = 'buygame61_bot'
DEEPSEEK_API_KEY = "sk-8d6e9d7c39c84ec6a0ecba379674346d"
ADMIN_ID = 1475910449  # ← ЗАМЕНИ НА СВОЙ TELEGRAM ID (узнать можно через @userinfobot)

client_openai = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# ==================== ФАЙЛЫ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"
LEARNING_FILE = "learning_progress.json"
HOUSES_FILE = "player_houses.json"
SHOPS_FILE = "player_shops.json"
AUCTION_FILE = "auction_data.json"
LEADERBOARD_FILE = "leaderboard.json"
SKINS_FILE = "player_skins.json"
SKIN_INVENTORY_FILE = "skin_inventory.json"
SUPPLIER_ITEMS_FILE = "supplier_items.json"

SKINS = [
    # Бесплатные (за репутацию)
    {"id": "default", "name": "Новичок", "price": 0, "rarity": "обычный", "rep_required": 0, "emoji": "👶", "description": "Базовый скин.", "avatar_config": {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}, "image_url": "AgACAgIAAxkBAAIDHGn4w7w3AAGnzzdBPwI4mNZEgoIjsAACzhhrG8bbwEsN1TBcMS6PhwEAAwIAA3kAAzsE", "limited": False, "max_count": 0},
    {"id": "hustler", "name": "Темщик", "price": 0, "rarity": "обычный", "rep_required": 25, "emoji": "😎", "description": "Репутация 🟢 Хорошая (25).", "avatar_config": {"face": "cool", "hair": "mohawk", "clothes": "jacket", "accessory": "sunglasses", "background": "gray"}, "image_url": "AgACAgIAAxkBAAIDLGn4xLrV_G5vUn9b0lfZbRt9uSNpAAIjE2sbRxXIS2ta2c2uvaRDAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "boss", "name": "Мажор", "price": 0, "rarity": "обычный", "rep_required": 50, "emoji": "🕴", "description": "Репутация 🔵 Отличная (50).", "avatar_config": {"face": "cool", "hair": "short", "clothes": "suit", "accessory": "glasses", "background": "blue"}, "image_url": "AgACAgIAAxkBAAIDIGn4w8SxLumhkkue8rlTXiUqetBaAALQGGsbxtvAS3sUKevJKpGYAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    # Платные
    {"id": "coffee", "name": "Кофейный барыга", "price": 25000, "rarity": "редкий", "rep_required": 0, "emoji": "💻", "description": "Редкий скин.", "avatar_config": {"face": "smile", "hair": "cap", "clothes": "rich", "accessory": "chain", "background": "purple"}, "image_url": "AgACAgIAAxkBAAIDImn4w8m4lmlm6AYS1kBkt8Dx7ZyXAAL9GGsbxtvAS_vggWeGPBAgAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "cyber", "name": "Кибер-барыга", "price": 80000, "rarity": "эпический", "rep_required": 0, "emoji": "🤖", "description": "Эпический скин.", "avatar_config": {"face": "surprised", "hair": "none", "clothes": "hoodie", "accessory": "headphones", "background": "blue"}, "image_url": "AgACAgIAAxkBAAIDxWn45SvUS8m2sFIRTRarzV3ylymgAAJGFGsbRxXISwzuA4OGtBJyAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "casual", "name": "Кэжуал барыга", "price": 5000, "rarity": "обычный", "rep_required": 0, "emoji": "👕", "description": "Обычный скин. Повседневный стиль.", "avatar_config": {"face": "default", "hair": "short", "clothes": "hoodie", "accessory": "none", "background": "white"}, "image_url": "AgACAgIAAxkBAAIDyWn45lfPG9qMGWwqqtVvghaY-OpXAAJPFGsbRxXIS30JjvcuwnwHAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "cyberpunk", "name": "Барыга-киберпанк", "price": 120000, "rarity": "эпический", "rep_required": 0, "emoji": "🦾", "description": "Эпический скин в стиле киберпанк.", "avatar_config": {"face": "cool", "hair": "mohawk", "clothes": "jacket", "accessory": "sunglasses", "background": "purple"}, "image_url": "AgACAgIAAxkBAAIDy2n45wzQNDGj-mZOhvUo3ToyI8MVAAJTFGsbRxXIS-Qrt13FcYnwAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "legend", "name": "Бог товарки", "price": 150000, "rarity": "легендарный", "rep_required": 0, "emoji": "👑", "description": "Легендарный скин.", "avatar_config": {"face": "cool", "hair": "long", "clothes": "rich", "accessory": "headphones", "background": "green"}, "image_url": "AgACAgIAAxkBAAIDJGn4w8wheVk6HY-7qpII5w8hQ4lyAAL_GGsbxtvAS2S7TonuV3alAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "oldmoney", "name": "Олд мани барыга", "price": 180000, "rarity": "эпический", "rep_required": 0, "emoji": "🎩", "description": "Эпический скин в стиле old money.", "avatar_config": {"face": "cool", "hair": "short", "clothes": "suit", "accessory": "glasses", "background": "blue"}, "image_url": "AgACAgIAAxkBAAIDzWn457hhlWHg6jBASBq0EcTDmWEpAAJUFGsbRxXIS1Xa-QcoURaAAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    {"id": "bazaar", "name": "Базарный барыга", "price": 35000, "rarity": "редкий", "rep_required": 0, "emoji": "🗣", "description": "Редкий скин. Настоящий базарный.", "avatar_config": {"face": "angry", "hair": "cap", "clothes": "jacket", "accessory": "chain", "background": "gray"}, "image_url": "AgACAgIAAxkBAAID0Wn46ouAFjuzjq1yQyOG4FahoM-CAAJlFGsbRxXIS-9X56WNZeVnAQADAgADeQADOwQ", "limited": False, "max_count": 0},
    # Лимитированный мифический
    {"id": "creator", "name": "Создатель", "price": 0, "rarity": "мифический", "rep_required": 0, "emoji": "💎", "description": "💎 МИФИЧЕСКИЙ СКИН. Лимит: 3 шт. Только для избранных.", "avatar_config": {"face": "cool", "hair": "cap", "clothes": "rich", "accessory": "chain", "background": "purple"}, "image_url": "AgACAgIAAxkBAAIDz2n46ShGgxc6Z-mfB73cEzOvS74oAAJjFGsbRxXIS67XdFNB5viXAQADAgADeQADOwQ", "limited": True, "max_count": 3},
]

RARITY_COLORS = {"обычный": "⬜", "редкий": "🟦", "эпический": "🟪", "легендарный": "🟨", "мифический": "💎"}


# Сортировка скинов от обычных к мифическим
RARITY_ORDER = {"обычный": 0, "редкий": 1, "эпический": 2, "легендарный": 3, "мифический": 4}
SKINS.sort(key=lambda x: RARITY_ORDER.get(x["rarity"], 0))

# ==================== ОБЩИЕ ТОВАРЫ У ПОСТАВЩИКОВ ====================
SUPPLIER_ITEM_RARITIES = {
    "обычный": {"name": "Обычный", "color": "⬜", "price_mult_min": 0.8, "price_mult_max": 1.3, "chance": 55},
    "редкий": {"name": "Редкий", "color": "🟦", "price_mult_min": 1.5, "price_mult_max": 2.5, "chance": 25},
    "эпический": {"name": "Эпический", "color": "🟪", "price_mult_min": 2.5, "price_mult_max": 5.0, "chance": 12},
    "легендарный": {"name": "Легендарный", "color": "🟨", "price_mult_min": 5.0, "price_mult_max": 12.0, "chance": 6},
    "мифический": {"name": "Мифический", "color": "🟥", "price_mult_min": 10.0, "price_mult_max": 30.0, "chance": 2},
}

supplier_stock = {"items": [], "last_update": 0}

def generate_supplier_items():
    items = []
    for _ in range(random.randint(6, 10)):
        rarities = list(SUPPLIER_ITEM_RARITIES.keys())
        weights = [SUPPLIER_ITEM_RARITIES[r]["chance"] for r in rarities]
        rarity = random.choices(rarities, weights=weights, k=1)[0]
        rd = SUPPLIER_ITEM_RARITIES[rarity]
        base = random.choice(BASE_ITEMS)
        mp = int(base["base_price"] * random.uniform(rd["price_mult_min"], rd["price_mult_max"]))
        bp = int(mp * random.uniform(0.6, 0.85))
        items.append({
            "name": f"{rd['color']} {base['cat']} {base['name']}",
            "cat": base["cat"], "buy_price": bp, "market_price": mp,
            "rarity": rarity, "rarity_name": rd["name"], "rarity_color": rd["color"],
            "end_time": time_module.time() + random.randint(300, 900),
            "id": random.randint(10000, 99999)
        })
    supplier_stock["items"] = items
    supplier_stock["last_update"] = time_module.time()
    save_json(SUPPLIER_ITEMS_FILE, supplier_stock)

def check_supplier_update():
    if time_module.time() - supplier_stock.get("last_update", 0) >= 300 or not supplier_stock.get("items"):
        generate_supplier_items()
        return True
    if supplier_stock.get("items"):
        supplier_stock["items"] = [i for i in supplier_stock["items"] if i["end_time"] > time_module.time()]
        save_json(SUPPLIER_ITEMS_FILE, supplier_stock)
    return False

BASE_ITEMS = [
    {"cat": "👖 Джинсы", "name": "Levi's 501 Vintage", "base_price": 2000},
    {"cat": "👖 Джинсы", "name": "Carhartt WIP Denim", "base_price": 3500},
    {"cat": "👕 Худи", "name": "Adidas Originals Hoodie", "base_price": 2500},
    {"cat": "👕 Худи", "name": "Nike ACG Fleece", "base_price": 3000},
    {"cat": "🧥 Куртки", "name": "The North Face Nuptse", "base_price": 5000},
    {"cat": "🧥 Куртки", "name": "Alpha Industries MA-1", "base_price": 4000},
    {"cat": "👟 Кроссы", "name": "Nike Air Max 90", "base_price": 3500},
    {"cat": "👟 Кроссы", "name": "Adidas Samba OG", "base_price": 2800},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]
MARKET_EVENTS = [
    {"text": "📰 Хайп на джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Куртки в цене!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Кроссовки в тренде!", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
]

CLIENT_TYPES = {
    "angry": {"system_prompt": "Ты покупатель. Торгуешься.", "discount_range": (0.6, 0.8), "patience": 3},
    "kind": {"system_prompt": "Ты покупатель. Вежливый.", "discount_range": (0.85, 0.95), "patience": 5},
    "sly": {"system_prompt": "Ты перекупщик.", "discount_range": (0.7, 0.85), "patience": 4},
}

JOBS = [
    {"id": "flyers", "name": "📦 Расклейка объявлений", "duration": 60, "reward": 200, "emoji": "📦"},
    {"id": "delivery", "name": "🚗 Доставка заказов", "duration": 120, "reward": 500, "emoji": "🚗"},
    {"id": "freelance", "name": "💻 Фриланс (дизайн)", "duration": 300, "reward": 1200, "emoji": "💻"},
]

HOUSES = [
    {"id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0, "description": "Бесплатное жильё.", "image_url": "AgACAgIAAxkBAAIDw2n45KI6ja7rOv30n_8DdrWCFQwyAAI-FGsbRxXIS4VB50007zQ3AQADAgADeQADOwQ"},
    {"id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150, "description": "Уютная квартира. +150₽/день.", "image_url": "AgACAgIAAxkBAAIBeGn3hGvVcFktYFQJP-YNnKti48v1AAKYGWsbUNy4SzN3yqU-dPZwAQADAgADeQADOwQ"},
    {"id": "house", "name": "🏠 Одноэтажный дом", "price": 35000, "income_bonus": 400, "description": "Дом с гаражом. +400₽/день.", "image_url": "AgACAgIAAxkBAAIBemn3hKeq-IxdQ6l6jB7sD10pQPbHAAKUGGsbaAW5S4jG5ecluTqMAQADAgADeQADOwQ"},
    {"id": "villa", "name": "🏰 Богатая вилла", "price": 100000, "income_bonus": 1200, "description": "Вилла с бассейном. +1200₽/день.", "image_url": "AgACAgIAAxkBAAIBfGn3hME0a5rsH1wos1Qyy1AhsYAnAAKVGGsbaAW5SzyFR-E8--65AQADAgADeQADOwQ"},
    {"id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000, "description": "Яхта у причала. +3000₽/день.", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
]

SHOP_LEVELS = [
    {"id": "none", "name": "Нет магазина", "price": 0, "income_per_hour": 0},
    {"id": "stall", "name": "🛍 Лавка на рынке", "price": 5000, "income_per_hour": 100},
    {"id": "container", "name": "📦 Контейнер на Садоводе", "price": 15000, "income_per_hour": 300},
    {"id": "store", "name": "🏬 Магазин в ТЦ", "price": 50000, "income_per_hour": 800},
    {"id": "boutique", "name": "👑 Бутик в центре", "price": 150000, "income_per_hour": 2000},
]

REPUTATION_LEVELS = {-100: "💀 ЧС", -50: "🔴 Ужасная", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 75: "🟣 Легенда", 100: "👑 Бог товарки"}

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()
    writing_description = State()

# ==================== ХРАНИЛИЩА ====================
players = {}
referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False})
rep_data = {}
learning_data = {}
active_chats = {}
published_items = {}
sold_items = defaultdict(set)
last_bot_message = {}
pending_messages = defaultdict(list)
active_chat_for_user = {}
side_jobs = {}
supply_drop = {}  # {user_id: {"items": [...], "found": [...], "clicks": int, "active": bool}}
player_houses = {}
player_shops = {}
player_skins = {}
skin_inventory = {}  # {user_id: ["skin_id1", "skin_id2", ...]}
item_descriptions = {}
auction_data = {"items": []}
leaderboard_data = {}

# ==================== ЗАГРУЗКА ====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data, learning_data, player_houses, player_shops, player_skins, auction_data, leaderboard_data, supplier_stock, skin_inventory
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})
    player_houses = load_json(HOUSES_FILE, {})
    player_shops = load_json(SHOPS_FILE, {})
    player_skins = load_json(SKINS_FILE, {})
    auction_data = load_json(AUCTION_FILE, {"items": []})
    leaderboard_data = load_json(LEADERBOARD_FILE, {})
    supplier_stock = load_json(SUPPLIER_ITEMS_FILE, {"items": [], "last_update": 0})
    skin_inventory = load_json(SKIN_INVENTORY_FILE, {})

load_all()
check_supplier_update()

# ==================== ЧИСТКА ====================
async def del_prev(user_id):
    if user_id in last_bot_message:
        try: await bot.delete_message(user_id, last_bot_message[user_id])
        except: pass

async def del_user_msgs(user_id):
    for msg_id in pending_messages.get(user_id, []):
        try: await bot.delete_message(user_id, msg_id)
        except: pass
    pending_messages[user_id] = []

async def send_msg(user_id, text, parse_mode="HTML", reply_markup=None):
    await del_prev(user_id); await del_user_msgs(user_id)
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

# ==================== РЕФЕРАЛЫ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"

# ==================== РЕПУТАЦИЯ ====================
def get_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data: rep_data[uid] = {"score": 0, "total_sales": 0, "total_profit": 0}
    return rep_data[uid]

def rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t: return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount): 
    get_rep(user_id)["score"] = max(-100, min(100, get_rep(user_id)["score"] + amount))
    save_json(REPUTATION_FILE, rep_data)

def update_leaderboard(user_id, profit, sales):
    uid = str(user_id); week = datetime.now().strftime("%Y-W%W")
    if uid not in leaderboard_data or leaderboard_data[uid].get("week") != week:
        leaderboard_data[uid] = {"total_profit": 0, "total_sales": 0, "week": week}
    leaderboard_data[uid]["total_profit"] += profit
    leaderboard_data[uid]["total_sales"] += sales
    save_json(LEADERBOARD_FILE, leaderboard_data)

def get_top_players(limit=10):
    top = [(int(uid), d["total_profit"], d["total_sales"]) for uid, d in leaderboard_data.items()]
    top.sort(key=lambda x: x[1], reverse=True)
    return top[:limit]

# ==================== СКИНЫ ====================
def get_player_skin(user_id):
    uid = str(user_id)
    if uid not in player_skins: player_skins[uid] = "default"
    return player_skins[uid]

def buy_skin(user_id, skin_id):
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    if not skin: return False, "Не найден"
    if get_player_skin(user_id) == skin_id: return False, "Уже надет!"
    
    # Проверка лимитированных скинов
    if skin.get("limited"):
        count = sum(1 for uid, s in player_skins.items() if s == skin_id)
        if count >= skin["max_count"]:
            return False, f"Лимит исчерпан! ({skin['max_count']} шт.)"
    
    p = get_player(user_id)
    if skin["price"] > 0 and p["balance"] < skin["price"]: return False, "Недостаточно!"
    if skin["price"] > 0: p["balance"] -= skin["price"]
    
    # Добавляем в инвентарь скинов
    add_skin_to_inventory(user_id, skin_id)
    
    # Надеваем скин
    player_skins[str(user_id)] = skin_id
    save_json(SKINS_FILE, player_skins)
    return True, f"✅ {skin['name']}!"

def check_rep_skins(user_id):
    rep_score = get_rep(user_id)["score"]
    return [s for s in SKINS if s["rep_required"] > 0 and rep_score >= s["rep_required"] and get_player_skin(user_id) != s["id"]]

def get_skin_inventory(user_id):
    uid = str(user_id)
    if uid not in skin_inventory:
        skin_inventory[uid] = []
    return skin_inventory[uid]

def add_skin_to_inventory(user_id, skin_id):
    uid = str(user_id)
    if uid not in skin_inventory:
        skin_inventory[uid] = []
    if skin_id not in skin_inventory[uid]:
        skin_inventory[uid].append(skin_id)
        save_json(SKIN_INVENTORY_FILE, skin_inventory)
        return True
    return False

def remove_skin_from_inventory(user_id, skin_id):
    uid = str(user_id)
    if uid in skin_inventory and skin_id in skin_inventory[uid]:
        skin_inventory[uid].remove(skin_id)
        save_json(SKIN_INVENTORY_FILE, skin_inventory)
        return True
    return False

# ==================== НЕДВИЖИМОСТЬ ====================
def get_player_house(user_id):
    uid = str(user_id)
    if uid not in player_houses: player_houses[uid] = "room"
    return player_houses[uid]

def buy_house(user_id, house_id):
    house = next((h for h in HOUSES if h["id"] == house_id), None)
    if not house: return False, "Не найден"
    if get_player_house(user_id) == house_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < house["price"]: return False, "Недостаточно!"
    p["balance"] -= house["price"]; player_houses[str(user_id)] = house_id
    save_json(HOUSES_FILE, player_houses)
    return True, f"✅ {house['name']}!"

# ==================== МАГАЗИН ====================
def get_player_shop(user_id):
    uid = str(user_id)
    if uid not in player_shops: player_shops[uid] = {"level": "none", "last_collect": time_module.time()}
    return player_shops[uid]

def buy_shop(user_id, shop_id):
    shop = next((s for s in SHOP_LEVELS if s["id"] == shop_id), None)
    if not shop: return False, "Не найден"
    if get_player_shop(user_id)["level"] == shop_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < shop["price"]: return False, "Недостаточно!"
    p["balance"] -= shop["price"]
    player_shops[str(user_id)]["level"] = shop_id
    save_json(SHOPS_FILE, player_shops)
    return True, f"✅ {shop['name']}!"

def collect_shop_income(user_id):
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(user_id)["level"]), SHOP_LEVELS[0])
    if shop["id"] == "none": return 0
    elapsed = time_module.time() - get_player_shop(user_id)["last_collect"]
    income = int(shop["income_per_hour"] * (elapsed / 3600))
    if income > 0:
        get_player_shop(user_id)["last_collect"] = time_module.time()
        if user_id in players: players[user_id]["balance"] += income
    return income

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    return players[user_id]

def market_price(base, demand): return int(base * demand * random.uniform(0.9, 1.3))
def daily_event(): return random.choice(MARKET_EVENTS) if random.random() < 0.6 else None

def apply_event(p, event):
    if event["cat"]: p["market_demand"][event["cat"]] = max(0.3, min(3.0, p["market_demand"][event["cat"]] * event["mult"]))
    else:
        for cat in CATEGORIES: p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat] * event["mult"]))

def fmt_demand(p):
    return "\n".join(f"{'🔥' if m>=1.5 else '📈' if m>=1.2 else '➡️' if m>=0.8 else '📉' if m>=0.5 else '💀'} {c}: x{m:.1f}" for c, m in p["market_demand"].items())

def get_active_buyers_count(user_id):
    return sum(1 for c in active_chats.values() if c["user_id"] == user_id and not c["finished"])

# ==================== МЕНЮ С ФОТО СКИНА ====================
async def send_menu_with_skin(user_id, text, page=1):
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    kb = main_kb(page, user_id)
    if skin.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, skin["image_url"], caption=text, parse_mode="HTML", reply_markup=kb)
            await del_prev(user_id); last_bot_message[user_id] = msg.message_id
            return
        except: pass
    await send_msg(user_id, text, reply_markup=kb)

def main_kb(page=1, user_id=None):
    bc = get_active_buyers_count(user_id) if user_id else 0
    cl = f"💬 ЧАТЫ ({bc})" if bc > 0 else "💬 ЧАТЫ"
    if page == 1:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="action_buy"), InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
            [InlineKeyboardButton(text=cl, callback_data="action_chats"), InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="action_auction")],
            [InlineKeyboardButton(text="💼 РАБОТА", callback_data="action_job"), InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand")],
            [InlineKeyboardButton(text="🎮 МИНИ-ИГРЫ", callback_data="action_minigames")],
            [InlineKeyboardButton(text="⏩ ДЕНЬ ВПЕРЁД", callback_data="action_nextday")],
            [InlineKeyboardButton(text="➡️ ВКЛАДКА 2", callback_data="menu_page_2")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 ЖИЛЬЁ", callback_data="action_houses"), InlineKeyboardButton(text="🏪 МАГАЗИН", callback_data="action_shop")],
        [InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins")],
        [InlineKeyboardButton(text="🏆 ЛИДЕРЫ", callback_data="action_leaderboard")],
        [InlineKeyboardButton(text="📊 СТАТЫ", callback_data="action_stats"), InlineKeyboardButton(text="🏅 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
        [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
        [InlineKeyboardButton(text="⬅️ ВКЛАДКА 1", callback_data="menu_page_1"), InlineKeyboardButton(text="🏁 КОНЕЦ", callback_data="action_end")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
    ])

# ==================== ОЦЕНКА ОПИСАНИЯ ====================
def rate_description(desc):
    score = 3
    if len(desc) >= 30: score += 1
    if len(desc) >= 80: score += 1
    keywords = ["состояние", "размер", "цвет", "бренд", "качество", "материал", "новый"]
    score += min(3, sum(1 for w in keywords if w in desc.lower()))
    return min(10, max(1, score))

def get_quality_bonus(q):
    if q >= 9: return {"name": "🔥 Легендарное", "buyers_bonus": 3}
    elif q >= 7: return {"name": "⭐ Отличное", "buyers_bonus": 2}
    elif q >= 5: return {"name": "👍 Хорошее", "buyers_bonus": 1}
    return {"name": "👌 Обычное", "buyers_bonus": 0}

# ==================== НЕЙРОКЛИЕНТЫ ====================
def first_msg(client_type, item_name, price, offer):
    msgs = {
        "angry": [f"По {item_name}. {price}₽ дорого. {offer}₽.", f"{item_name}. Давайте {offer}₽?"],
        "kind": [f"Добрый день! {item_name}. Может {offer}₽?", f"{item_name}. Устроит {offer}₽?"],
        "sly": [f"Привет! {item_name}. Рынок — {offer}₽.", f"{item_name}. Готов на {offer}₽."],
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer(user_id, buyer_id, client_type, item_name, price, is_reminder=False):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    if not is_reminder:
        discount = random.uniform(*client["discount_range"]); discount = max(0.3, min(0.95, discount))
        offer = int(price * discount); offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        msg = first_msg(client_type, item_name, price, offer)
        active_chats[chat_key] = {"user_id": user_id, "buyer_id": buyer_id, "client_type": client_type, "item": item_name, "price": price, "offer": offer, "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}], "round": 1, "max_rounds": client["patience"], "finished": False}
        await send_msg(user_id, f"📩 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n💬 {msg}")
    else:
        chat = active_chats.get(chat_key)
        if chat and not chat["finished"]:
            # Без ИИ — простое напоминание
            reminders = [
                f"Жду ответ по {item_name}.",
                f"Вы тут? Я всё ещё жду.",
                f"Ответьте пожалуйста по {item_name}.",
            ]
            chat["history"].append({"role": "assistant", "content": random.choice(reminders)})
            await send_msg(user_id, f"🔔 <b>Покупатель #{buyer_id}</b>\n💬 {random.choice(reminders)}")

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(15, 45))
    if user_id not in published_items or not published_items[user_id]: return
    pub = published_items[user_id]; item = pub["item"]
    if item["name"] in sold_items[user_id]: return
    n = random.randint(1, 3)
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    await send_msg(user_id, f"📱 <b>ОБЪЯВЛЕНИЕ!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n👥 Пишут: <b>{n}</b> чел.")
    for i, bt in enumerate(types):
        await asyncio.sleep(random.randint(5, 20))
        await send_buyer(user_id, i + 1, bt, item["name"], item["market_price"])

async def complete_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    p = get_player(user_id); item_name = chat["item"]; final = chat["offer"]
    if item_name in sold_items[user_id]: return None
    sold = None
    if user_id in published_items and published_items[user_id]:
        pub_item = published_items[user_id].get("item", {})
        if pub_item.get("name") == item_name: sold = pub_item; published_items[user_id] = None
    if not sold:
        for i, inv in enumerate(p["inventory"]):
            if inv["name"] == item_name: sold = p["inventory"].pop(i); break
    if not sold: return None
    sold_items[user_id].add(item_name)
    profit = final - sold["buy_price"]
    p["balance"] += final; p["total_earned"] += profit; p["items_sold"] += 1
    p["stat_earned_today"] += profit
    add_rep(user_id, random.randint(2, 5))
    update_leaderboard(user_id, profit, 1)
    chat["finished"] = True
    if user_id in active_chat_for_user: del active_chat_for_user[user_id]
    if message: await send_msg(user_id, f"🎉 <b>ПРОДАНО!</b>\n📦 {item_name}\n💰 Цена: {final}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽")
    return profit

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id; args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        for uid in referral_data:
            if gen_ref(uid) == ref_code and uid != str(user_id):
                if user_id not in referral_data[uid]["invited"]:
                    referral_data[uid]["invited"].append(user_id)
                    save_json(REFERRAL_FILE, dict(referral_data))
                    
                    if int(uid) in players:
                        players[int(uid)]["balance"] += 10000
                        add_rep(int(uid), 5)
                    
                    try:
                        await bot.send_message(
                            int(uid),
                            "🎉 <b>НОВЫЙ РЕФЕРАЛ!</b>\n\n"
                            "По твоей ссылке новый игрок!\n"
                            "💰 Ты получил: +10 000₽\n"
                            "⭐ Репутация: +5\n"
                            f"👥 Всего: {len(referral_data[uid]['invited'])} чел.",
                            parse_mode="HTML"
                        )
                    except: pass
                    
                    await del_user_msgs(user_id)
                    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
                    await send_msg(
                        user_id,
                        "🎁 <b>РЕФЕРАЛЬНЫЙ БОНУС!</b>\n\n"
                        "Ты перешёл по ссылке и получишь +5 000₽ при старте!\n\n"
                        f"Твой скин: {skin['emoji']} {skin['name']}\n\n"
                        "<i>Приглашай друзей — 10 000₽ за каждого!</i>",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
                            [InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins")],
                        ])
                    )
                    return
                break
    # Стандартное приветствие для всех
    await del_user_msgs(user_id)
    if user_id == ADMIN_ID and get_player_skin(user_id) != "creator":
        buy_skin(user_id, "creator")
    for skin in check_rep_skins(user_id):
        buy_skin(user_id, skin["id"])
        await send_msg(user_id, f"🎉 <b>НОВЫЙ СКИН!</b>\n{skin['emoji']} {skin['name']} — за репутацию {rep_level(get_rep(user_id)['score'])}!")
    p = players.get(user_id)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    if p and p.get("day", 0) > 0:
        txt = f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n📅 День {p['day']} | 💰 {p['balance']}₽\n👤 Скин: {skin['emoji']} {skin['name']}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins")],
            [InlineKeyboardButton(text="🔄 ЗАНОВО", callback_data="restart_game_confirm")],
        ])
    else:
        txt = f"🎮 <b>RESELL TYCOON</b>\n\nТвой скин: {skin['emoji']} {skin['name']}\n\nРедкие товары • Скины • Аукцион\nЛидеры • Магазин • Подработки"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins")],
        ])
    if skin.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, skin["image_url"], caption=txt, parse_mode="HTML", reply_markup=kb)
            last_bot_message[user_id] = msg.message_id
        except: await send_msg(user_id, txt, reply_markup=kb)
    else: await send_msg(user_id, txt, reply_markup=kb)

# ==================== АДМИН-КОМАНДЫ ====================
@dp.message(Command('admin'))
async def admin_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return await message.answer("❌ Нет доступа!")
    
    args = message.text.split()
    
    if len(args) < 2:
        return await message.answer(
            "🔑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
            "<b>Команды:</b>\n"
            "/admin players — список игроков\n"
            "/admin give [ID] [сумма] — выдать деньги\n"
            "/admin skin [ID] [skin_id] — выдать скин\n"
            "/admin reset [ID] — сбросить игрока",
            parse_mode="HTML"
        )
    
    cmd = args[1]
    
    if cmd == "players":
        txt = "👥 <b>ИГРОКИ:</b>\n\n"
        for uid, p in players.items():
            try:
                user = await bot.get_chat(uid)
                name = user.first_name or f"ID:{uid}"
            except:
                name = f"ID:{uid}"
            txt += f"🆔 {name} (ID: {uid})\n💰 {p['balance']}₽ | 📅 День {p['day']} | 📋 Продано: {p['items_sold']}\n\n"
        await message.answer(txt or "Нет активных игроков.", parse_mode="HTML")
    
    elif cmd == "give" and len(args) >= 4:
        target_id = int(args[2])
        amount = int(args[3])
        if target_id in players:
            players[target_id]["balance"] += amount
            await message.answer(f"✅ Выдано {amount}₽ игроку ID:{target_id}")
            try:
                await bot.send_message(target_id, f"💰 <b>Админ выдал {amount}₽!</b>\n💼 Новый баланс: {players[target_id]['balance']}₽", parse_mode="HTML")
            except: pass
        else:
            await message.answer("❌ Игрок не найден.")
    
    elif cmd == "reset" and len(args) >= 3:
        target_id = int(args[2])
        if target_id in players:
            del players[target_id]
            await message.answer(f"✅ Игрок ID:{target_id} сброшен.")
        else:
            await message.answer("❌ Игрок не найден.")
    
    elif cmd == "skin" and len(args) >= 4:
        target_id = int(args[2])
        skin_id = args[3]
        if target_id in players:
            success, msg = buy_skin(target_id, skin_id)
            await message.answer(f"{'✅' if success else '❌'} {msg}")
        else:
            await message.answer("❌ Игрок не найден.")

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await send_menu_with_skin(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}")

# ==================== ЧАТ С ПОКУПАТЕЛЯМИ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    if not message.text: return
    user_id = message.from_user.id; text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    # Продажа только по явным словам (без цифр)
    for w in ["продано", "забирай", "отдаю", "продам", "бери"]:
        if w in text.lower():
            # Если есть цена — это торг, не продажа
            if "₽" not in text:
                target = None
                if user_id in active_chat_for_user and active_chat_for_user[user_id] in active_chats:
                    target = active_chats[active_chat_for_user[user_id]]
                else:
                    for key, chat in active_chats.items():
                        if chat["user_id"] == user_id and not chat["finished"]:
                            target = chat; break
                if target:
                    target["finished"] = True
                    if user_id in active_chat_for_user: del active_chat_for_user[user_id]
                    await send_msg(user_id, f"👤 <b>Покупатель #{target['buyer_id']}:</b> Договорились на {target['offer']}₽!")
                    await complete_sale(user_id, target["buyer_id"], message)
                    return
    
    # Поиск активного диалога
    chat_key = None
    if user_id in active_chat_for_user and active_chat_for_user[user_id] in active_chats:
        chat_key = active_chat_for_user[user_id]
    else:
        for key, chat in active_chats.items():
            if chat["user_id"] == user_id and not chat["finished"]:
                chat_key = key; break
    
    if not chat_key: return
    chat = active_chats[chat_key]
    chat["history"].append({"role": "user", "content": text}); chat["round"] += 1
    
    if chat["round"] >= 3:
        chat["finished"] = True
        if random.random() < 0.6:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Ладно, {chat['offer']}₽!")
            await complete_sale(user_id, chat["buyer_id"], message)
        else:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Извините, передумал.")
        return
    
    # Первые 2 раунда — DeepSeek, дальше — простые ответы
    if chat["round"] <= 2:
        try:
            sp = CLIENT_TYPES[chat["client_type"]]["system_prompt"] + f"\nТовар: {chat['item']}. Твоя цена: {chat['offer']}₽."
            resp = client_openai.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": sp}] + chat["history"][-2:], temperature=0.7, max_tokens=30)
            ai_msg = resp.choices[0].message.content
        except:
            ai_msg = random.choice([f"Берёте за {chat['offer']}₽?", f"Ну так что?", f"Ладно, давайте {chat['offer']}₽."])
    else:
        ai_msg = random.choice([
            f"Берёте за {chat['offer']}₽?",
            f"Ну так что?",
            f"Ладно, давайте {chat['offer']}₽.",
            f"Я жду ответ.",
            f"Решайтесь!",
        ])
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    for w in ["беру", "договорились", "по рукам", "забираю", "согласен"]:
        if w in ai_msg.lower() and "?" not in ai_msg.lower():
            chat["finished"] = True
            await complete_sale(user_id, chat["buyer_id"], message)
            return
    
    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}")

# ==================== ЧАТЫ ====================
@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    al = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    if not al: return await send_msg(user_id, "💬 Нет диалогов.\nОпубликуй товар в 📦 Инвентаре!")
    txt = f"💬 <b>ДИАЛОГИ ({len(al)}):</b>\n\n"
    kb = []
    for key, chat in al:
        txt += f"👤 #{chat['buyer_id']} | {chat['item']} | {chat['offer']}₽\n"
        kb.append([InlineKeyboardButton(text=f"💬 Ответить #{chat['buyer_id']}", callback_data=f"open_chat_{user_id}_{chat['buyer_id']}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="menu_page_1")])
    await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data.startswith("open_chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_"); user_id = int(parts[2]); buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    if chat_key not in active_chats or active_chats[chat_key]["finished"]: return await callback.answer("Диалог завершён")
    active_chat_for_user[user_id] = chat_key
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"💬 <b>ДИАЛОГ #{buyer_id}</b>\nПиши «продано» чтобы продать!")

# ==================== КАТАЛОГ СКИНОВ ====================
@dp.callback_query(F.data == "action_skins")
async def show_skins_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt = "👤 <b>МАГАЗИН СКИНОВ</b>\n\nВыбери категорию:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 ПЛАТНЫЕ СКИНЫ", callback_data="skins_paid")],
        [InlineKeyboardButton(text="🏆 ЗА ДОСТИЖЕНИЯ", callback_data="skins_free")],
        [InlineKeyboardButton(text="🎒 ИНВЕНТАРЬ СКИНОВ", callback_data="skins_inventory")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
    ])
    await send_msg(user_id, txt, reply_markup=kb)
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "skins_paid")
async def show_skins_paid(callback: CallbackQuery, page: int = 0):
    paid_skins = [s for s in SKINS if s["rep_required"] == 0 and s["price"] > 0 and not s.get("limited")]
    await show_skins_catalog(callback, page, paid_skins, "💰 ПЛАТНЫЕ СКИНЫ")

@dp.callback_query(F.data == "skins_free")
async def show_skins_free(callback: CallbackQuery, page: int = 0):
    free_skins = [s for s in SKINS if (s["rep_required"] > 0 or s["price"] == 0) and not s.get("limited")]
    await show_skins_catalog(callback, page, free_skins, "🏆 ЗА ДОСТИЖЕНИЯ")

async def show_skins_catalog(callback: CallbackQuery, page: int, skin_list: list, title: str):
    user_id = callback.from_user.id
    if page < 0: page = 0
    if page >= len(skin_list): page = len(skin_list) - 1
    if not skin_list:
        return await send_msg(user_id, "В этой категории пока нет скинов.")
    
    skin = skin_list[page]; owned = get_player_skin(user_id) == skin["id"]
    p = get_player(user_id); rep_score = get_rep(user_id)["score"]
    rc = RARITY_COLORS.get(skin["rarity"], "⬜")
    
    txt = f"👤 <b>{title}</b>\n📄 {page+1}/{len(skin_list)}\n\n{skin['emoji']} <b>{skin['name']}</b>\n{rc} {skin['rarity'].upper()}\n📝 {skin['description']}\n"
    
    if owned: txt += "\n✅ <b>НАДЕТ</b>"; act = None
    elif skin["rep_required"] > 0:
        if rep_score >= skin["rep_required"]: txt += "\n🎁 <b>ДОСТУПЕН!</b>"; act = InlineKeyboardButton(text="🎁 ПОЛУЧИТЬ", callback_data=f"buy_skin_{skin['id']}")
        else: txt += f"\n🔒 Нужно {skin['rep_required']} реп. (у тебя {rep_score})"; act = None
    else:
        if skin.get("limited"):
            skin_id = skin["id"]
            count = sum(1 for uid, s in player_skins.items() if s == skin_id)
            available = skin["max_count"] - count
            if available <= 0:
                txt += f"\n💎 <b>ЛИМИТ ИСЧЕРПАН</b>"; act = None
            else:
                txt += f"\n🔒 <b>ТОЛЬКО ПО ВЫДАЧЕ</b>"; act = None
        else:
            if p["balance"] >= skin["price"]: txt += f"\n💰 Цена: {skin['price']}₽"; act = InlineKeyboardButton(text=f"🛒 КУПИТЬ", callback_data=f"buy_skin_{skin['id']}")
            else: txt += f"\n❌ {skin['price']}₽ (не хватает {skin['price']-p['balance']}₽)"; act = None
    
    txt += f"\n\n💼 {p['balance']}₽ | ⭐ {rep_score}/100"
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"skinlist_{title}_{page-1}"))
    if page < len(skin_list)-1: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"skinlist_{title}_{page+1}"))
    
    kb = []
    if nav: kb.append(nav)
    if act: kb.append([act])
    kb.append([InlineKeyboardButton(text="🔙 К КАТЕГОРИЯМ", callback_data="action_skins")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    if skin.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, skin["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await del_prev(user_id); last_bot_message[user_id] = msg.message_id
            try: await callback.message.delete()
            except: pass
        except: await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("skinlist_"))
async def skinlist_page_btn(callback: CallbackQuery):
    parts = callback.data.split("_")
    title = parts[1]
    page = int(parts[2])
    
    if "ПЛАТНЫЕ" in title:
        paid_skins = [s for s in SKINS if s["rep_required"] == 0 and s["price"] > 0]
        await show_skins_catalog(callback, page, paid_skins, "💰 ПЛАТНЫЕ СКИНЫ")
    else:
        free_skins = [s for s in SKINS if s["rep_required"] > 0 or s["price"] == 0]
        await show_skins_catalog(callback, page, free_skins, "🏆 ЗА ДОСТИЖЕНИЯ")

@dp.callback_query(F.data == "skins_inventory")
async def show_skins_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    inv = get_skin_inventory(user_id)
    
    if not inv:
        return await send_msg(user_id, "🎒 <b>ИНВЕНТАРЬ СКИНОВ ПУСТ</b>\n\nКупи скины в магазине или получи за достижения!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 В МАГАЗИН", callback_data="action_skins")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ]))
    
    txt = "🎒 <b>ТВОИ СКИНЫ:</b>\n\n"
    kb = []
    current_skin = get_player_skin(user_id)
    
    for skin_id in inv:
        skin = next((s for s in SKINS if s["id"] == skin_id), None)
        if skin:
            active = "✅ НАДЕТ" if skin_id == current_skin else ""
            txt += f"{skin['emoji']} {skin['name']} ({skin['rarity']}) {active}\n"
            if skin_id != current_skin:
                kb.append([InlineKeyboardButton(text=f"👕 НАДЕТЬ: {skin['emoji']} {skin['name']}", callback_data=f"equip_skin_{skin_id}")])
            if skin["price"] > 0:
                kb.append([InlineKeyboardButton(text=f"📤 ПРОДАТЬ: {skin['emoji']} {skin['name']} за {int(skin['price']*0.7)}₽", callback_data=f"sell_skin_{skin_id}")])
    
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data.startswith("equip_skin_"))
async def equip_skin_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    skin_id = callback.data.replace("equip_skin_", "")
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    if skin:
        player_skins[str(user_id)] = skin_id
        save_json(SKINS_FILE, player_skins)
        await callback.answer(f"Надет: {skin['name']}!")
        await show_skins_inventory(callback)
    else:
        await callback.answer("Скин не найден")

@dp.callback_query(F.data.startswith("sell_skin_"))
async def sell_skin_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    skin_id = callback.data.replace("sell_skin_", "")
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    
    if not skin:
        return await callback.answer("Скин не найден")
    
    if get_player_skin(user_id) == skin_id:
        return await callback.answer("Сначала сними скин!")
    
    if skin["price"] == 0:
        return await callback.answer("Бесплатные скины нельзя продать!")
    
    sell_price = int(skin["price"] * 0.7)
    p = get_player(user_id)
    p["balance"] += sell_price
    remove_skin_from_inventory(user_id, skin_id)
    
    await callback.answer(f"Продан за {sell_price}₽!")
    await send_msg(user_id, f"💰 <b>СКИН ПРОДАН!</b>\n{skin['emoji']} {skin['name']}\n💵 Получено: {sell_price}₽\n💼 Баланс: {p['balance']}₽")
    await show_skins_inventory(callback)

@dp.callback_query(F.data.startswith("buy_skin_"))
async def buy_skin_btn(callback: CallbackQuery):
    user_id = callback.from_user.id; skin_id = callback.data.replace("buy_skin_", "")
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    if not skin: return await callback.answer("Не найден")
    if skin["rep_required"] > 0 and get_rep(user_id)["score"] < skin["rep_required"]: return await callback.answer(f"Нужно {skin['rep_required']} реп.!")
    success, msg = buy_skin(user_id, skin_id)
    if success: await callback.answer(msg); await show_skins_menu(callback)
    else: await callback.answer(msg, show_alert=True)

# ==================== ЗАКУПКА ====================
@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id; check_supplier_update()
    items = supplier_stock.get("items", [])
    if not items: generate_supplier_items(); items = supplier_stock.get("items", [])
    txt = "🏭 <b>ПОСТАВЩИКИ</b>\n<i>Обновление каждые 5 мин. Общие для всех!</i>\n\n"
    kb = []; p = get_player(user_id)
    for item in items[:8]:
        tl = max(0, int(item["end_time"] - time_module.time())); mins = tl // 60
        txt += f"{item['rarity_color']} {item['name']} — {item['buy_price']}₽ ({mins}м)\n"
        if p["balance"] >= item["buy_price"]: kb.append([InlineKeyboardButton(text=f"{item['rarity_color']} {item['name']} — {item['buy_price']}₽", callback_data=f"buy_supplier_{item['id']}")])
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data="action_buy")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data.startswith("buy_supplier_"), StateFilter(GameState.playing))
async def buy_supplier_item(callback: CallbackQuery):
    user_id = callback.from_user.id; item_id = int(callback.data.replace("buy_supplier_", ""))
    item = next((it for it in supplier_stock.get("items", []) if it["id"] == item_id), None)
    if not item: return await callback.answer("Товар уже купили!")
    if item["end_time"] < time_module.time(): return await callback.answer("Время истекло!")
    p = get_player(user_id)
    if p["balance"] < item["buy_price"]: return await callback.answer("❌ Мало денег!")
    p["balance"] -= item["buy_price"]
    p["inventory"].append({"name": item["name"], "cat": item["cat"], "buy_price": item["buy_price"], "market_price": item["market_price"]})
    supplier_stock["items"] = [it for it in supplier_stock.get("items", []) if it["id"] != item_id]
    save_json(SUPPLIER_ITEMS_FILE, supplier_stock)
    await callback.answer("✅ Куплен!")
    await send_msg(user_id, f"🛒 <b>КУПЛЕНО!</b>\n📦 {item['name']}\n💰 Закуп: {item['buy_price']}₽\n📊 Рынок: ~{item['market_price']}₽\n👇 📦 Инвентарь → Опубликовать!")

# ==================== МАГАЗИН ====================
@dp.callback_query(F.data == "action_shop", StateFilter(GameState.playing))
async def show_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(user_id)["level"]), SHOP_LEVELS[0])
    elapsed = time_module.time() - get_player_shop(user_id)["last_collect"]
    income = int(shop["income_per_hour"] * (elapsed / 3600))
    p = get_player(user_id)
    txt = f"🏪 <b>МАГАЗИН ОДЕЖДЫ</b>\n\nТвой: {shop['name']}\n💰 Доход: {shop['income_per_hour']}₽/час\n💵 Накоплено: {income}₽\n💼 Баланс: {p['balance']}₽"
    kb = []
    if income > 0: kb.append([InlineKeyboardButton(text=f"💰 СОБРАТЬ +{income}₽", callback_data="collect_shop_income")])
    for s in SHOP_LEVELS:
        if s["price"] > shop["price"] and p["balance"] >= s["price"]: kb.append([InlineKeyboardButton(text=f"🛒 {s['name']} — {s['price']}₽", callback_data=f"buy_shop_{s['id']}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "collect_shop_income", StateFilter(GameState.playing))
async def collect_shop_income_btn(callback: CallbackQuery):
    income = collect_shop_income(callback.from_user.id)
    await callback.answer(f"✅ Собрано {income}₽!" if income > 0 else "Пока нечего")
    await show_shop(callback)

@dp.callback_query(F.data.startswith("buy_shop_"), StateFilter(GameState.playing))
async def buy_shop_btn(callback: CallbackQuery):
    success, msg = buy_shop(callback.from_user.id, callback.data.replace("buy_shop_", ""))
    if success: await callback.answer(msg); await show_shop(callback)
    else: await callback.answer(msg, show_alert=True)

# ==================== АУКЦИОН ====================
@dp.callback_query(F.data == "action_auction", StateFilter(GameState.playing))
async def show_auction(callback: CallbackQuery):
    ai = [item for item in auction_data.get("items", []) if item.get("active", True)]
    if not ai: return await send_msg(callback.from_user.id, "🔨 <b>АУКЦИОН</b>\n\nНет лотов.\nВыстави свой товар!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    txt = "🔨 <b>АУКЦИОН</b>\n\n"; kb = []
    for i, item in enumerate(ai):
        tl = max(0, int(item.get("end_time", 0) - time_module.time())); h, m = divmod(tl, 3600)
        txt += f"📦 Лот #{i+1}: {item['item']['name']}\n💰 {item.get('current_bid', item['start_price'])}₽\n⏳ {int(h)}ч {int(m)}м\n\n"
        if item["seller_id"] != callback.from_user.id: kb.append([InlineKeyboardButton(text=f"💰 СТАВКА (мин. {int(item.get('current_bid', item['start_price']) * 1.1)}₽)", callback_data=f"auction_bid_{i}")])
    kb.append([InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await send_msg(callback.from_user.id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "auction_sell", StateFilter(GameState.playing))
async def auction_sell_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    kb = []
    
    # Товары из инвентаря
    for i, item in enumerate(p["inventory"]):
        kb.append([InlineKeyboardButton(text=f"📦 {item['name']} (~{item['market_price']}₽)", callback_data=f"auction_put_{i}")])
    
    # Скины из инвентаря
    skin_inv = get_skin_inventory(user_id)
    current = get_player_skin(user_id)
    for sid in skin_inv:
        s = next((sk for sk in SKINS if sk["id"] == sid), None)
        if s and s["price"] > 0 and sid != current:
            kb.append([InlineKeyboardButton(text=f"👤 Скин: {s['emoji']} {s['name']}", callback_data=f"auction_skin_{sid}")])
    
    if not kb:
        return await callback.answer("Нечего выставить!")
    
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_auction")])
    await send_msg(user_id, "📤 <b>ВЫСТАВИТЬ НА АУКЦИОН</b>\n\nВыбери товар или скин:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass
    await callback.answer()

@dp.callback_query(F.data.startswith("auction_put_"), StateFilter(GameState.playing))
async def auction_put_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[2])
    p = get_player(user_id)
    
    if item_idx >= len(p["inventory"]):
        return await callback.answer("Товар не найден")
    
    item = p["inventory"].pop(item_idx)
    
    # Добавляем на аукцион
    auction_data["items"].append({
        "seller_id": user_id,
        "item": item,
        "start_price": item["market_price"],
        "current_bid": item["market_price"],
        "bidder_id": None,
        "end_time": time_module.time() + 3600,
        "active": True
    })
    save_json(AUCTION_FILE, auction_data)
    
    await callback.answer("✅ Лот выставлен!")
    await send_msg(user_id, f"📤 <b>ЛОТ НА АУКЦИОНЕ!</b>\n📦 {item['name']}\n💰 Старт: {item['market_price']}₽\n⏳ 1 час")

# ==================== ПУБЛИКАЦИЯ ====================
@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    await state.set_state(GameState.writing_description)
    await state.update_data(publish_item_idx=item_idx)
    await send_msg(user_id, f"✍️ <b>ОПИШИ ТОВАР</b>\n\n📦 {p['inventory'][item_idx]['name']}\n💰 Цена: {p['inventory'][item_idx]['market_price']}₽\n\nНапиши описание в чат.")

@dp.message(StateFilter(GameState.writing_description))
async def handle_description(message: types.Message, state: FSMContext):
    if not message.text: return
    user_id = message.from_user.id; desc = message.text.strip()
    data = await state.get_data(); item_idx = data.get("publish_item_idx", 0)
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): await state.set_state(GameState.playing); return
    item = p["inventory"][item_idx]
    quality = rate_description(desc)
    if user_id not in item_descriptions: item_descriptions[user_id] = {}
    item_descriptions[user_id][item["name"]] = {"description": desc, "quality": quality}
    published_items[user_id] = {"item": item.copy()}
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"📢 <b>ОПУБЛИКОВАНО!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n📝 Качество: {get_quality_bonus(quality)['name']} ({quality}/10)\n⏳ Жди 1-3 минуты!")
    asyncio.create_task(spawn_buyers(user_id))

# ==================== МИНИ-ИГРЫ ====================
@dp.callback_query(F.data == "action_minigames", StateFilter(GameState.playing))
async def show_minigames(callback: CallbackQuery):
    user_id = callback.from_user.id
    txt = "🎮 <b>МИНИ-ИГРЫ</b>\n\nВыбери игру:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 РАЗБЕРИ ПОСТАВКУ (1000₽)", callback_data="action_supply")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
    ])
    await send_msg(user_id, txt, reply_markup=kb)
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "action_supply", StateFilter(GameState.playing))
async def show_supply(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    
    if user_id in supply_drop and supply_drop[user_id].get("active"):
        drop = supply_drop[user_id]
        remaining = 10 - drop["clicks"]
        
        if remaining <= 0:
            txt = f"📦 <b>ПОСТАВКА РАЗОБРАНА!</b>\n\n🎁 Найдено {len(drop['found'])} вещей:\n"
            for item in drop["found"]:
                txt += f"• {item['name']} (~{item['market_price']}₽)\n"
            for item in drop["found"]:
                p["inventory"].append(item)
            supply_drop[user_id]["active"] = False
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 НОВАЯ ПОСТАВКА", callback_data="action_supply")],
                [InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")],
                [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
            ])
            await send_msg(user_id, txt, reply_markup=kb)
            try: await callback.message.delete()
            except: pass
            return
        else:
            txt = f"📦 <b>РАЗБЕРИ ПОСТАВКУ</b>\n\n📸 Осталось кликов: {remaining}\n🎁 Найдено: {len(drop['found'])} вещей\n\n<i>Жми кнопку!</i>"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📦 РАЗОБРАТЬ ({remaining})", callback_data="supply_click")],
            ])
            await send_msg(user_id, txt, reply_markup=kb)
            try: await callback.message.delete()
            except: pass
            return
    
    if p["balance"] < 10000:
        return await callback.answer("Нужно 10 000₽!")

    p["balance"] -= 10000

    items_in_box = []
    for _ in range(random.randint(2, 5)):
        rarity_roll = random.randint(1, 100)
        if rarity_roll <= 60:
            rarity = "обычный"
        elif rarity_roll <= 85:
            rarity = "редкий"
        elif rarity_roll <= 95:
            rarity = "эпический"
        elif rarity_roll <= 99:
            rarity = "легендарный"
        else:
            rarity = "мифический"

        rd = SUPPLIER_ITEM_RARITIES[rarity]
        base = random.choice(BASE_ITEMS)
        mp = int(base["base_price"] * random.uniform(rd["price_mult_min"], rd["price_mult_max"]))
        items_in_box.append({
            "name": f"{rd['color']} {base['cat']} {base['name']}",
            "cat": base["cat"],
            "buy_price": int(mp * 0.5),
            "market_price": mp,
            "rarity": rarity
        })
    
    supply_drop[user_id] = {"items": items_in_box, "found": [], "clicks": 0, "active": True}
    
    txt = (
        f"📦 <b>СЕКРЕТНЫЙ БОКС ОТ ПОСТАВЩИКА!</b>\n\n"
        f"Ты купил коробку с неизвестным товаром.\n"
        f"Как на реальной оптовке — никогда не знаешь,\n"
        f"попадётся там брендовая вещь или обычный мусор.\n\n"
        f"💰 Оплачено: 10 000₽\n"
        f"📸 Нужно открыть: 10 раз\n"
        f"🎁 Товаров внутри: {len(items_in_box)} шт.\n\n"
        f"<i>Жми кнопку чтобы разбирать коробку!\n"
        f"Шанс найти что-то ценное — 40%</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 РАЗОБРАТЬ (10)", callback_data="supply_click")],
    ])
    await send_msg(user_id, txt, reply_markup=kb)
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "supply_click", StateFilter(GameState.playing))
async def supply_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in supply_drop or not supply_drop[user_id].get("active"):
        return await callback.answer("Нет активной поставки!")
    
    drop = supply_drop[user_id]
    drop["clicks"] += 1
    
    if random.random() < 0.4 and drop["items"]:
        item = random.choice(drop["items"])
        drop["items"].remove(item)
        drop["found"].append(item)
        await callback.answer(f"🎁 {item['name']}!")
    else:
        msgs = ["📦 Коробка...", "🔍 Ищешь...", "📸 Смотришь...", "👀 Что там?", "📦 Пусто..."]
        await callback.answer(random.choice(msgs))
    
    await show_supply(callback)

# ==================== ПОДРАБОТКИ ====================
@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    kb = [[InlineKeyboardButton(text=f"{j['emoji']} {j['name']} — {j['reward']}₽ ({j['duration']}с)", callback_data=f"start_job_{i}")] for i, j in enumerate(JOBS)]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await send_msg(callback.from_user.id, "💼 <b>ПОДРАБОТКИ</b>\n\nВыбери работу:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data.startswith("start_job_"))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id; job_idx = int(callback.data.split("_")[2])
    side_jobs[user_id] = {"job_type": job_idx, "start_time": time_module.time(), "done": False}
    job = JOBS[job_idx]
    await send_msg(user_id, f"💼 <b>РАБОТАЕМ!</b>\n{job['emoji']} {job['name']}\n💰 {job['reward']}₽\n⏱ {job['duration']} сек.")
    await callback.answer("Приступил!")
    asyncio.create_task(finish_job(user_id, job_idx))

async def finish_job(user_id, job_idx):
    await asyncio.sleep(JOBS[job_idx]["duration"])
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        side_jobs[user_id]["done"] = True
        if user_id in players: players[user_id]["balance"] += JOBS[job_idx]["reward"]
        try: await send_msg(user_id, f"✅ <b>ГОТОВО!</b>\n💰 +{JOBS[job_idx]['reward']}₽")
        except: pass

# ==================== ОСТАЛЬНЫЕ CALLBACK ====================
@dp.callback_query(F.data == "action_leaderboard", StateFilter(GameState.playing))
async def show_leaderboard(callback: CallbackQuery):
    top = get_top_players(10)
    if not top: return await send_msg(callback.from_user.id, "🏆 Пока нет данных.")
    txt = "🏆 <b>ТОП-10 ПРОДАВЦОВ НЕДЕЛИ</b>\n\n"
    for i, (uid, profit, sales) in enumerate(top):
        try: name = (await bot.get_chat(uid)).first_name or f"ID:{uid}"
        except: name = f"ID:{uid}"
        txt += f"{['🥇','🥈','🥉'][i] if i<3 else f'{i+1}.'} {name} — {profit}₽ ({sales} прод.)\n"
    await send_msg(callback.from_user.id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "action_houses", StateFilter(GameState.playing))
async def show_houses_catalog(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id; current_id = get_player_house(user_id); p = get_player(user_id)
    if page < 0: page = 0
    if page >= len(HOUSES): page = len(HOUSES) - 1
    house = HOUSES[page]; owned = current_id == house["id"]
    st = "✅ ТВОЁ" if owned else (f"💰 {house['price']}₽" if p["balance"] >= house["price"] else f"💰 {house['price']}₽ (не хватает {house['price']-p['balance']}₽)")
    act = InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data=f"buy_house_{house['id']}") if not owned and p["balance"] >= house["price"] else None
    txt = f"🏠 <b>НЕДВИЖИМОСТЬ</b>\n📄 {page+1}/{len(HOUSES)}\n\n{house['name']}\n{house.get('description', '')}\n{st}\n\n💼 Баланс: {p['balance']}₽"
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"house_page_{page-1}"))
    if page < len(HOUSES)-1: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"house_page_{page+1}"))
    kb = []
    if nav: kb.append(nav)
    if act: kb.append([act])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    # Отправляем фото
    if house.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await del_prev(user_id); last_bot_message[user_id] = msg.message_id
            try: await callback.message.delete()
            except: pass
            return
        except: pass
    await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data.startswith("house_page_"), StateFilter(GameState.playing))
async def house_page_btn(callback: CallbackQuery):
    await show_houses_catalog(callback, int(callback.data.split("_")[2]))

@dp.callback_query(F.data.startswith("buy_house_"), StateFilter(GameState.playing))
async def buy_house_btn(callback: CallbackQuery):
    success, msg = buy_house(callback.from_user.id, callback.data.replace("buy_house_", ""))
    if success: await callback.answer(msg); await show_houses_catalog(callback)
    else: await callback.answer(msg, show_alert=True)

@dp.callback_query(F.data == "menu_page_1")
async def menu_page_1(callback: CallbackQuery):
    p = get_player(callback.from_user.id); skin = next((s for s in SKINS if s["id"] == get_player_skin(callback.from_user.id)), SKINS[0])
    await send_menu_with_skin(callback.from_user.id, f"📅 <b>МЕНЮ 1/2</b>\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", 1)
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "menu_page_2")
async def menu_page_2(callback: CallbackQuery):
    p = get_player(callback.from_user.id); skin = next((s for s in SKINS if s["id"] == get_player_skin(callback.from_user.id)), SKINS[0])
    await send_menu_with_skin(callback.from_user.id, f"📅 <b>МЕНЮ 2/2</b>\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", 2)
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]; event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await send_menu_with_skin(user_id, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n💰 5 000₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}")

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; p = players.get(user_id)
    if not p:
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
        p = players[user_id]; event = daily_event(); p["current_event"] = event
        if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await send_menu_with_skin(user_id, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}")

@dp.callback_query(F.data == "restart_game_confirm")
async def restart_confirm(callback: CallbackQuery):
    await send_msg(callback.from_user.id, "⚠️ <b>СБРОСИТЬ ПРОГРЕСС?</b>\nБаланс и инвентарь потеряются.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚠️ ДА", callback_data="restart_game_yes")], [InlineKeyboardButton(text="❌ НЕТ", callback_data="continue_game")]]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "restart_game_yes")
async def restart_yes(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await start_new_game_btn(callback, state)

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(callback.from_user.id)), HOUSES[0])
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(callback.from_user.id)["level"]), SHOP_LEVELS[0])
    await send_msg(callback.from_user.id, f"📊 <b>СТАТИСТИКА</b>\n💰 Баланс: {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n🛒 Потрачено: {p['total_spent']}₽\n🏠 Жильё: {house['name']}\n🏪 Магазин: {shop['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    
    # Применяем погодные эффекты
    weathers = [
        {"name": "☀️ Солнечно", "effect_cat": "👕 Худи", "effect_mult": 1.3, "desc": "Спрос на худи и футболки вырос!"},
        {"name": "🌧 Дождливо", "effect_cat": "🧥 Куртки", "effect_mult": 1.4, "desc": "Все ищут куртки и дождевики!"},
        {"name": "❄️ Холодно", "effect_cat": "🧥 Куртки", "effect_mult": 1.5, "desc": "Зима близко — спрос на куртки взлетел!"},
        {"name": "🌤 Облачно", "effect_cat": "👖 Джинсы", "effect_mult": 1.2, "desc": "Джинсы и плотная одежда в тренде."},
        {"name": "🌪 Ветрено", "effect_cat": "👟 Кроссы", "effect_mult": 0.7, "desc": "В такую погоду меньше покупают."},
    ]
    
    weather = random.choice(weathers)
    
    # Применяем эффект на 1 игровой день
    if weather["effect_cat"] in p["market_demand"]:
        p["market_demand"][weather["effect_cat"]] *= weather["effect_mult"]
        p["market_demand"][weather["effect_cat"]] = max(0.3, min(3.0, p["market_demand"][weather["effect_cat"]]))
    
    # Случайная рыночная ситуация
    situations = [
        {"name": "📈 Рынок растёт", "mult": 1.1, "desc": "Общий спрос повысился!"},
        {"name": "📉 Рынок падает", "mult": 0.85, "desc": "Покупатели экономят."},
        {"name": "🔥 Ажиотаж", "mult": 1.3, "desc": "Все скупают всё подряд!"},
        {"name": "💤 Затишье", "mult": 0.9, "desc": "Мало покупателей на рынке."},
        {"name": "➡️ Стабильность", "mult": 1.0, "desc": "Рынок без изменений."},
    ]
    
    situation = random.choice(situations)
    
    # Применяем общий эффект
    if situation["mult"] != 1.0:
        for cat in p["market_demand"]:
            p["market_demand"][cat] *= situation["mult"]
            p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat]))
    
    txt = (
        f"📊 <b>СИТУАЦИЯ НА РЫНКЕ</b>\n\n"
        f"🌍 <b>Погода:</b> {weather['name']}\n"
        f"   {weather['desc']}\n\n"
        f"📊 <b>Ситуация:</b> {situation['name']}\n"
        f"   {situation['desc']}\n\n"
        f"<b>Спрос по категориям:</b>\n"
        f"{fmt_demand(p)}\n\n"
        f"💡 <b>Совет:</b> "
    )
    
    max_cat = max(p["market_demand"], key=p["market_demand"].get)
    max_val = p["market_demand"][max_cat]
    
    if max_val >= 1.5:
        txt += f"Сейчас лучше всего продавать {max_cat} — спрос высокий! 🔥"
    elif max_val >= 1.2:
        txt += f"Обрати внимание на {max_cat} — спрос растёт! 📈"
    else:
        txt += "Рынок спокойный. Закупайся дёшево и жди роста! ⏳"
    
    await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu_callback(callback: CallbackQuery):
    u = get_rep(callback.from_user.id)
    lvl = rep_level(u['score'])
    bar = "█" * int((u['score']+100)/200*10) + "░" * (10-int((u['score']+100)/200*10))
    txt = f"🏅 <b>РЕПУТАЦИЯ: {lvl}</b>\n📊 [{bar}] {u['score']}/100\n\n📦 Всего продаж: {u['total_sales']}\n💰 Общая прибыль: {u['total_profit']}₽\n\n<i>Повышай репутацию — получай скины!</i>"
    await send_msg(callback.from_user.id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = len(referral_data[str(user_id)]["invited"])
    total_bonus = count * 10000  # 10 000₽ за каждого друга
    txt = (
        f"🔗 <b>РЕФЕРАЛЬНАЯ СИСТЕМА</b>\n\n"
        f"Твоя ссылка:\n<code>{ref_link(user_id)}</code>\n\n"
        f"👥 Приглашено: {count} чел.\n"
        f"💰 Заработано: {total_bonus}₽\n"
        f"⭐ Бонус: +5 репутации за друга\n\n"
        f"<b>🎁 Награды:</b>\n"
        f"• Ты получаешь <b>10 000₽</b> за каждого друга\n"
        f"• Друг получает <b>5 000₽</b> стартового бонуса\n"
        f"• 5 друзей — скин «Темщик» бесплатно\n"
        f"• 10 друзей — скин «Мажор» бесплатно\n\n"
        f"<i>Отправь ссылку другу и получай бонусы!</i>"
    )
    await send_msg(callback.from_user.id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 КОПИРОВАТЬ ССЫЛКУ", callback_data=f"copy_ref_{user_id}")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
    ]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data.startswith("copy_ref_"))
async def copy_ref_btn(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    await callback.message.answer(f"🔗 Твоя реферальная ссылка:\n<code>{ref_link(user_id)}</code>", parse_mode="HTML")
    await callback.answer("Ссылка отправлена! 📋")

# ==================== ИНВЕНТАРЬ ====================
@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    if not p["inventory"]: return await send_msg(callback.from_user.id, "📦 <b>ИНВЕНТАРЬ ПУСТ</b>\n\nКупи товары у поставщиков! 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="action_buy")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    kb = [[InlineKeyboardButton(text=f"{it['name']} | {it['buy_price']}₽ → ~{it['market_price']}₽", callback_data=f"inv_{i}")] for i, it in enumerate(p["inventory"])]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    txt = "📦 <b>ИНВЕНТАРЬ</b>\n\n" + "\n".join(f"{i+1}. {it['name']}\n   Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"]))
    txt += "\n\n👇 <b>Нажми на товар чтобы опубликовать!</b>"
    await send_msg(callback.from_user.id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

# ==================== СЛЕДУЮЩИЙ ДЕНЬ ====================
@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    bonus = house["income_bonus"]; shop_income = collect_shop_income(user_id)
    p["balance"] += bonus; p["day"] += 1
    # Обновляем спрос
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    # Залежавшиеся товары теряют в цене
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
    if user_id in published_items: published_items[user_id] = None
    sold_items[user_id].clear()
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    txt = f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽\n👤 {skin['emoji']} {skin['name']}\n🏠 Доход от {house['name']}: +{bonus}₽"
    if shop_income > 0: txt += f"\n🏪 Магазин: +{shop_income}₽"
    txt += f"\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}"
    await send_menu_with_skin(user_id, txt)

# ==================== ЗАВЕРШЕНИЕ ИГРЫ ====================
@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    p = get_player(callback.from_user.id); await state.clear()
    r = "🏆 <b>ПОБЕДА!</b> Ты раскрутился до 50 000₽!" if p["balance"] >= 50000 else "💀 <b>БАНКРОТ!</b> Ты потерял все деньги." if p["balance"] <= 0 else "🎮 <b>ИГРА ОКОНЧЕНА</b>"
    txt = f"{r}\n\n💰 Баланс: {p['balance']}₽\n📦 Продано товаров: {p['items_sold']}\n💸 Всего заработано: {p['total_earned']}₽\n\n/play — начать заново!"
    await send_msg(callback.from_user.id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 НАЧАТЬ ЗАНОВО", callback_data="restart_game")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    try: await callback.message.delete()
    except: pass

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await send_msg(callback.from_user.id, "🔄 Напиши /play чтобы начать новую игру!")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await send_menu_with_skin(user_id, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}")

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    skin = next((s for s in SKINS if s["id"] == get_player_skin(callback.from_user.id)), SKINS[0])
    await send_msg(callback.from_user.id, f"🎮 <b>RESELL TYCOON</b>\n👤 {skin['emoji']} {skin['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")]]))

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    l = get_learning(callback.from_user.id)
    kb = [[InlineKeyboardButton(text=f"{'✅' if lesson['id'] in l['completed'] else '📖'} {lesson['title']}", callback_data=f"lesson_{lesson['id']}")] for lesson in [{"id": 1, "title": "🚀 Основы", "text": "Основы товарного бизнеса", "reward": 500}, {"id": 2, "title": "📊 Рынок", "text": "Анализ рынка и спрос", "reward": 500}]]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="back_to_start")])
    await send_msg(callback.from_user.id, "📚 <b>ОБУЧЕНИЕ ТОВАРНОМУ БИЗНЕСУ</b>\n\nИзучай уроки и получай бонусы!", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon FULL запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())