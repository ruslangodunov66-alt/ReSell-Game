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
BOT_USERNAME = 'R-Game'
DEEPSEEK_API_KEY = "sk-8d6e9d7c39c84ec6a0ecba379674346d"

client_openai = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# ==================== ФАЙЛЫ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"
LEARNING_FILE = "learning_progress.json"
HOUSES_FILE = "player_houses.json"
AVATARS_FILE = "player_avatars.json"
SHOPS_FILE = "player_shops.json"
AUCTION_FILE = "auction_data.json"
LEADERBOARD_FILE = "leaderboard.json"
SKINS_FILE = "player_skins.json"
RARE_ITEMS_FILE = "rare_items.json"

# ==================== СКИНЫ (8 ШТУК) ====================
SKINS = [
    {"id": "default", "name": "👶 Новичок", "price": 0, "rarity": "common", "description": "Базовый скин.", "emoji": "👶", "avatar_config": {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}},
    {"id": "hustler", "name": "😎 Темщик", "price": 3000, "rarity": "common", "description": "Опытный перекупщик.", "emoji": "😎", "avatar_config": {"face": "cool", "hair": "mohawk", "clothes": "jacket", "accessory": "sunglasses", "background": "gray"}},
    {"id": "boss", "name": "🕴 Мажор", "price": 10000, "rarity": "common", "description": "Стиль и статус.", "emoji": "🕴", "avatar_config": {"face": "cool", "hair": "short", "clothes": "suit", "accessory": "glasses", "background": "blue"}},
    {"id": "rich", "name": "🤴 Бизнесмен", "price": 25000, "rarity": "rare", "description": "Владелец сети. Редкий.", "emoji": "🤴", "avatar_config": {"face": "smile", "hair": "cap", "clothes": "rich", "accessory": "chain", "background": "purple"}},
    {"id": "legend", "name": "👑 Олигарх", "price": 50000, "rarity": "rare", "description": "Элита товарки. Редкий.", "emoji": "👑", "avatar_config": {"face": "cool", "hair": "long", "clothes": "rich", "accessory": "headphones", "background": "green"}},
    {"id": "cyber", "name": "🤖 Кибер-барыга", "price": 80000, "rarity": "epic", "description": "Из будущего. Эпический.", "emoji": "🤖", "avatar_config": {"face": "surprised", "hair": "none", "clothes": "hoodie", "accessory": "headphones", "background": "blue"}},
    {"id": "gold", "name": "🥇 Золотой перекуп", "price": 150000, "rarity": "legendary", "description": "Чистое золото. Легендарный.", "emoji": "🥇", "avatar_config": {"face": "cool", "hair": "cap", "clothes": "rich", "accessory": "chain", "background": "purple"}},
    {"id": "devil", "name": "😈 Теневой барыга", "price": 300000, "rarity": "mythic", "description": "Мифический скин. Единственный в своём роде.", "emoji": "😈", "avatar_config": {"face": "angry", "hair": "mohawk", "clothes": "suit", "accessory": "sunglasses", "background": "gray"}},
]

# ==================== РЕДКИЕ ТОВАРЫ ====================
ITEM_RARITIES = {
    "common": {"name": "Обычный", "color": "⬜", "price_mult_min": 0.8, "price_mult_max": 1.2, "chance": 60},
    "rare": {"name": "Редкий", "color": "🟦", "price_mult_min": 1.5, "price_mult_max": 2.0, "chance": 25},
    "epic": {"name": "Эпический", "color": "🟪", "price_mult_min": 2.5, "price_mult_max": 4.0, "chance": 10},
    "legendary": {"name": "Легендарный", "color": "🟨", "price_mult_min": 5.0, "price_mult_max": 10.0, "chance": 4},
    "mythic": {"name": "Мифический", "color": "🟥", "price_mult_min": 10.0, "price_mult_max": 25.0, "chance": 1},
}

# Специальный редкий товар, который появляется раз в 3 минуты
rare_item_timer = {"last_spawn": time_module.time(), "current_item": None}

def generate_rare_item():
    """Генерирует редкий товар."""
    # Выбираем редкость
    rarities = list(ITEM_RARITIES.keys())
    weights = [ITEM_RARITIES[r]["chance"] for r in rarities]
    rarity = random.choices(rarities, weights=weights, k=1)[0]
    
    rarity_data = ITEM_RARITIES[rarity]
    base_item = random.choice(BASE_ITEMS)
    price_mult = random.uniform(rarity_data["price_mult_min"], rarity_data["price_mult_max"])
    base_price = int(base_item["base_price"] * price_mult)
    
    return {
        "name": f"{rarity_data['color']} {base_item['cat']} {base_item['name']}",
        "cat": base_item["cat"],
        "base_price": base_price,
        "rarity": rarity,
        "rarity_name": rarity_data["name"],
        "buy_price": int(base_price * 0.7),  # Закуп дешевле рынка
        "market_price": base_price,
    }

def check_rare_item_spawn():
    """Проверяет, не пора ли создать новый редкий товар."""
    elapsed = time_module.time() - rare_item_timer["last_spawn"]
    if elapsed >= 180:  # 3 минуты
        rare_item_timer["current_item"] = generate_rare_item()
        rare_item_timer["last_spawn"] = time_module.time()
        return True
    return False

# ==================== ОСТАЛЬНЫЕ ДАННЫЕ ====================
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

SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭", "desc": "Крупный оптовик."},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕", "desc": "Сток."},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒", "desc": "Перекуп."},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸", "desc": "Дёшево, риск."},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲", "desc": "Кинет."},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑", "desc": "VIP."}

CLIENT_TYPES = {
    "angry": {"system_prompt": "Ты покупатель. Недоверчивый. Торгуешься. 1-3 предложения.", "discount_range": (0.6, 0.8), "patience": 4},
    "kind": {"system_prompt": "Ты покупатель. Вежливый. 1-3 предложения.", "discount_range": (0.85, 0.95), "patience": 6},
    "sly": {"system_prompt": "Ты перекупщик. Хитрый. 1-3 предложения.", "discount_range": (0.7, 0.85), "patience": 5},
}

JOBS = [
    {"id": "flyers", "name": "📦 Расклейка", "duration": 60, "reward": 200, "emoji": "📦", "steps": ["📦 Взял...", "🏃 Бежишь...", "📌 Клеишь...", "✅ Готово!"]},
    {"id": "delivery", "name": "🚗 Доставка", "duration": 120, "reward": 500, "emoji": "🚗", "steps": ["🚗 Принял...", "📦 Забираешь...", "🛵 Едешь...", "✅ Доставлено!"]},
    {"id": "freelance", "name": "💻 Фриланс", "duration": 300, "reward": 1200, "emoji": "💻", "steps": ["💻 Редактор...", "🎨 Рисуешь...", "📤 Отправляешь...", "✅ Готово!"]},
]

HOUSES = [
    {"id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0, "description": "Бесплатное жильё.", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
    {"id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150, "description": "Уютная квартира. +150₽/день.", "image_url": "AgACAgIAAxkBAAIBeGn3hGvVcFktYFQJP-YNnKti48v1AAKYGWsbUNy4SzN3yqU-dPZwAQADAgADeQADOwQ"},
    {"id": "house", "name": "🏠 Дом", "price": 35000, "income_bonus": 400, "description": "Дом с гаражом. +400₽/день.", "image_url": "AgACAgIAAxkBAAIBemn3hKeq-IxdQ6l6jB7sD10pQPbHAAKUGGsbaAW5S4jG5ecluTqMAQADAgADeQADOwQ"},
    {"id": "villa", "name": "🏰 Вилла", "price": 100000, "income_bonus": 1200, "description": "Вилла с бассейном. +1200₽/день.", "image_url": "AgACAgIAAxkBAAIBfGn3hME0a5rsH1wos1Qyy1AhsYAnAAKVGGsbaAW5SzyFR-E8--65AQADAgADeQADOwQ"},
    {"id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000, "description": "Яхта у причала. +3000₽/день.", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
]

SHOP_LEVELS = [
    {"id": "none", "name": "❌ Нет магазина", "price": 0, "income_per_hour": 0, "description": "Нет магазина.", "emoji": "❌", "image_url": ""},
    {"id": "stall", "name": "🛍 Лавка на рынке", "price": 5000, "income_per_hour": 100, "description": "+100₽/час.", "emoji": "🛍", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
    {"id": "container", "name": "📦 Контейнер на Садоводе", "price": 15000, "income_per_hour": 300, "description": "+300₽/час.", "emoji": "📦", "image_url": "AgACAgIAAxkBAAIBeGn3hGvVcFktYFQJP-YNnKti48v1AAKYGWsbUNy4SzN3yqU-dPZwAQADAgADeQADOwQ"},
    {"id": "store", "name": "🏬 Магазин в ТЦ", "price": 50000, "income_per_hour": 800, "description": "+800₽/час.", "emoji": "🏬", "image_url": "AgACAgIAAxkBAAIBemn3hKeq-IxdQ6l6jB7sD10pQPbHAAKUGGsbaAW5S4jG5ecluTqMAQADAgADeQADOwQ"},
    {"id": "boutique", "name": "👑 Бутик в центре", "price": 150000, "income_per_hour": 2000, "description": "+2000₽/час.", "emoji": "👑", "image_url": "AgACAgIAAxkBAAIBfGn3hME0a5rsH1wos1Qyy1AhsYAnAAKVGGsbaAW5SzyFR-E8--65AQADAgADeQADOwQ"},
]

AVATAR_PARTS = {
    "face": {"name": "😶 Лицо", "options": {"default": "Обычное", "smile": "Улыбка", "cool": "Крутое", "angry": "Злое", "surprised": "Удивлённое"}},
    "hair": {"name": "💇 Причёска", "options": {"none": "Лысый", "short": "Короткие", "long": "Длинные", "mohawk": "Ирокез", "cap": "Кепка"}},
    "clothes": {"name": "👕 Одежда", "options": {"tshirt": "Футболка", "hoodie": "Худи", "suit": "Костюм", "jacket": "Куртка", "rich": "Премиум"}},
    "accessory": {"name": "🕶 Аксессуары", "options": {"none": "Ничего", "glasses": "Очки", "sunglasses": "Тёмные очки", "chain": "Цепь", "headphones": "Наушники"}},
    "background": {"name": "🎨 Фон", "options": {"white": "Белый", "gray": "Серый", "blue": "Синий", "green": "Зелёный", "purple": "Фиолетовый"}},
}

DEFAULT_AVATAR = {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}
REPUTATION_LEVELS = {-100: "💀 ЧС", -50: "🔴 Ужасная", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 75: "🟣 Легенда", 100: "👑 Бог товарки"}
ACHIEVEMENTS = [
    {"id": "first_sale", "name": "🎯 Первая продажа", "target": 1, "reward": 5},
    {"id": "seller_10", "name": "📦 Продавец", "target": 10, "reward": 10},
    {"id": "profit_5000", "name": "💰 Навар", "target": 5000, "reward": 5},
]

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()
    writing_description = State()
    auction_price = State()

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
player_houses = {}
player_avatars = {}
player_shops = {}
player_skins = {}
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
    global referral_data, rep_data, learning_data, player_houses, player_avatars, player_shops, player_skins, auction_data, leaderboard_data
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})
    player_houses = load_json(HOUSES_FILE, {})
    player_avatars = load_json(AVATARS_FILE, {})
    player_shops = load_json(SHOPS_FILE, {})
    player_skins = load_json(SKINS_FILE, {})
    auction_data = load_json(AUCTION_FILE, {"items": []})
    leaderboard_data = load_json(LEADERBOARD_FILE, {})

load_all()

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
    if reply_markup is None:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]])
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

async def edit_msg(message, text, parse_mode="HTML", reply_markup=None):
    await del_user_msgs(message.chat.id)
    try: await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except: pass

# ==================== РЕФЕРАЛЫ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"
def is_vip(user_id):
    s = [(uid, len(d["invited"])) for uid, d in referral_data.items()]
    s.sort(key=lambda x: x[1], reverse=True)
    return str(user_id) in [str(uid) for uid, _ in s[:3]]

# ==================== РЕПУТАЦИЯ ====================
def get_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {"score": 0, "total_sales": 0, "total_profit": 0, "achievements": []}
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t: return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount): 
    u = get_rep(user_id); u["score"] = max(-100, min(100, u["score"] + amount))
    save_json(REPUTATION_FILE, rep_data)

def rep_mult(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4}
    else: return {"supplier_discount": 1.0, "scam_reduce": 0.8}

def update_leaderboard(user_id, profit, sales):
    uid = str(user_id)
    current_week = datetime.now().strftime("%Y-W%W")
    if uid not in leaderboard_data or leaderboard_data[uid].get("week") != current_week:
        leaderboard_data[uid] = {"total_profit": 0, "total_sales": 0, "week": current_week}
    leaderboard_data[uid]["total_profit"] += profit
    leaderboard_data[uid]["total_sales"] += sales

def get_top_players(limit=10):
    top = [(int(uid), d["total_profit"], d["total_sales"]) for uid, d in leaderboard_data.items()]
    top.sort(key=lambda x: x[1], reverse=True)
    return top[:limit]

# ==================== НЕДВИЖИМОСТЬ ====================
def get_player_house(user_id):
    uid = str(user_id)
    if uid not in player_houses: player_houses[uid] = "room"; save_json(HOUSES_FILE, player_houses)
    return player_houses[uid]

def buy_house(user_id, house_id):
    uid = str(user_id)
    house = next((h for h in HOUSES if h["id"] == house_id), None)
    if not house: return False, "Дом не найден"
    if get_player_house(user_id) == house_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < house["price"]: return False, f"Недостаточно денег!"
    p["balance"] -= house["price"]; player_houses[uid] = house_id
    save_json(HOUSES_FILE, player_houses)
    return True, f"✅ Куплен {house['name']}!"

# ==================== СКИНЫ ====================
def get_player_skin(user_id):
    uid = str(user_id)
    if uid not in player_skins: player_skins[uid] = "default"; save_json(SKINS_FILE, player_skins)
    return player_skins[uid]

def buy_skin(user_id, skin_id):
    uid = str(user_id)
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    if not skin: return False, "Скин не найден"
    if get_player_skin(user_id) == skin_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < skin["price"]: return False, f"Недостаточно денег!"
    p["balance"] -= skin["price"]
    player_skins[uid] = skin_id
    save_json(SKINS_FILE, player_skins)
    return True, f"✅ Куплен {skin['name']}!"

def get_current_avatar_config(user_id):
    skin_id = get_player_skin(user_id)
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    if skin and skin_id != "default":
        return skin["avatar_config"].copy()
    return get_player_avatar(user_id)

# ==================== АВАТАРЫ ====================
def get_player_avatar(user_id):
    uid = str(user_id)
    if uid not in player_avatars: player_avatars[uid] = DEFAULT_AVATAR.copy(); save_json(AVATARS_FILE, player_avatars)
    return player_avatars[uid]

def update_avatar_part(user_id, part, value):
    uid = str(user_id)
    if uid not in player_avatars: player_avatars[uid] = DEFAULT_AVATAR.copy()
    player_avatars[uid][part] = value
    save_json(AVATARS_FILE, player_avatars)

def get_avatar_url(avatar_config):
    seed = hashlib.md5(str(avatar_config).encode()).hexdigest()[:10]
    return f"https://api.dicebear.com/7.x/pixel-art/svg?seed={seed}"

# ==================== МАГАЗИН ====================
def get_player_shop(user_id):
    uid = str(user_id)
    if uid not in player_shops: player_shops[uid] = {"level": "none", "last_collect": time_module.time()}; save_json(SHOPS_FILE, player_shops)
    return player_shops[uid]

def buy_shop(user_id, shop_id):
    uid = str(user_id)
    shop = next((s for s in SHOP_LEVELS if s["id"] == shop_id), None)
    if not shop: return False, "Не найден"
    if get_player_shop(user_id)["level"] == shop_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < shop["price"]: return False, "Недостаточно денег!"
    p["balance"] -= shop["price"]
    player_shops[uid]["level"] = shop_id
    player_shops[uid]["last_collect"] = time_module.time()
    save_json(SHOPS_FILE, player_shops)
    return True, f"✅ Куплен {shop['name']}!"

def collect_shop_income(user_id):
    shop_data = get_player_shop(user_id)
    shop = next((s for s in SHOP_LEVELS if s["id"] == shop_data["level"]), SHOP_LEVELS[0])
    if shop["id"] == "none": return 0
    elapsed = time_module.time() - shop_data["last_collect"]
    income = int(shop["income_per_hour"] * (elapsed / 3600))
    if income > 0:
        shop_data["last_collect"] = time_module.time()
        save_json(SHOPS_FILE, player_shops)
        if user_id in players: players[user_id]["balance"] += income
    return income

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": 0, "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    return players[user_id]

def item_price(base, sup): return int(base * sup["price_mult"])
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

# ==================== ДВУХСТРАНИЧНОЕ МЕНЮ ====================
def main_kb(page=1, user_id=None):
    if page == 1:
        buyers_count = get_active_buyers_count(user_id) if user_id else 0
        chat_label = f"💬 ЧАТЫ ({buyers_count})" if buyers_count > 0 else "💬 ЧАТЫ"
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
            [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
            [InlineKeyboardButton(text=chat_label, callback_data="action_chats"),
             InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="action_auction")],
            [InlineKeyboardButton(text="💼 ЗАРАБОТОК", callback_data="action_job")],
            [InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand"),
             InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")],
            [InlineKeyboardButton(text="💎 РЕДКИЕ ТОВАРЫ", callback_data="action_rare")],
            [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday")],
            [InlineKeyboardButton(text="➡️ СТРАНИЦА 2", callback_data="menu_page_2")],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 НЕДВИЖИМОСТЬ", callback_data="action_houses")],
            [InlineKeyboardButton(text="🏪 МАГАЗИН ОДЕЖДЫ", callback_data="action_shop")],
            [InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins"),
             InlineKeyboardButton(text="🎨 КАСТОМИЗАЦИЯ", callback_data="action_avatar")],
            [InlineKeyboardButton(text="🏆 ТАБЛИЦА ЛИДЕРОВ", callback_data="action_leaderboard")],
            [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats"),
             InlineKeyboardButton(text="🏅 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
            [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
            [InlineKeyboardButton(text="⬅️ СТРАНИЦА 1", callback_data="menu_page_1")],
            [InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
        ])

# ==================== ОЦЕНКА ОПИСАНИЯ ====================
def rate_description(description):
    score = 3
    if len(description) >= 30: score += 1
    if len(description) >= 80: score += 1
    keywords = ["состояние", "размер", "цвет", "бренд", "качество", "материал", "новый", "винтаж", "оригинал"]
    score += min(3, sum(1 for w in keywords if w in description.lower()))
    return min(10, max(1, score))

def get_quality_bonus(quality):
    if quality >= 9: return {"price_mult": 1.5, "buyers_bonus": 3, "name": "🔥 Легендарное"}
    elif quality >= 7: return {"price_mult": 1.3, "buyers_bonus": 2, "name": "⭐ Отличное"}
    elif quality >= 5: return {"price_mult": 1.1, "buyers_bonus": 1, "name": "👍 Хорошее"}
    else: return {"price_mult": 1.0, "buyers_bonus": 0, "name": "👌 Обычное"}

# ==================== НЕЙРОКЛИЕНТЫ ====================
def first_msg(client_type, item_name, price, offer):
    msgs = {
        "angry": [f"По {item_name}. {price}₽ дорого. {offer}₽.", f"Здравствуйте! {item_name}. Давайте {offer}₽?"],
        "kind": [f"Добрый день! {item_name} нравится. Может {offer}₽?", f"Здравствуйте! {item_name}. Устроит {offer}₽?"],
        "sly": [f"Привет! {item_name}. Рынок — {offer}₽.", f"По {item_name}. Готов на {offer}₽."],
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer(user_id, buyer_id, client_type, item_name, price, is_reminder=False):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    
    if not is_reminder:
        rm = rep_mult(get_rep(user_id)["score"])
        discount = random.uniform(*client["discount_range"]) + rm.get("haggle_bonus", 0)
        discount = max(0.3, min(0.95, discount))
        desc_data = item_descriptions.get(user_id, {}).get(item_name, {})
        discount += (get_quality_bonus(desc_data.get("quality", 5))["price_mult"] - 1.0) * 0.3
        discount = max(0.3, min(0.95, discount))
        
        offer = int(price * discount); offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        
        msg = first_msg(client_type, item_name, price, offer)
        active_chats[chat_key] = {"user_id": user_id, "buyer_id": buyer_id, "client_type": client_type, "item": item_name, "price": price, "offer": offer, "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}], "round": 1, "max_rounds": client["patience"], "finished": False}
        
        await send_msg(user_id, f"📩 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n💬 {msg}")
    else:
        chat = active_chats.get(chat_key)
        if not chat or chat["finished"]: return
        msg = f"Я жду ответ по {item_name}."
        chat["history"].append({"role": "assistant", "content": msg})
        await send_msg(user_id, f"🔔 <b>Покупатель #{buyer_id}</b>\n💬 {msg}")

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
    if user_id not in published_items or not published_items[user_id]: return
    pub = published_items[user_id]; item = pub["item"]
    if item["name"] in sold_items[user_id]: return
    
    n = random.randint(1, 3)
    desc_data = item_descriptions.get(user_id, {}).get(item["name"], {})
    n += get_quality_bonus(desc_data.get("quality", 5))["buyers_bonus"]
    n = max(1, min(6, n))
    
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    await send_msg(user_id, f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n👥 Пишут: <b>{n}</b> чел.")
    
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
        if pub_item.get("name") == item_name:
            sold = pub_item; published_items[user_id] = None
    
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
    if message:
        await send_msg(user_id, f"🎉 <b>ПРОДАНО!</b>\n📦 {item_name}\n💰 Цена: {final}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽")
    return profit

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id; args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        for uid in referral_data:
            if gen_ref(uid) == ref_code and uid != str(user_id):
                referral_data[uid]["invited"].append(user_id)
                save_json(REFERRAL_FILE, dict(referral_data))
                if int(uid) in players: players[int(uid)]["balance"] += 500
                try: await bot.send_message(int(uid), "🎉 Новый реферал! +500₽", parse_mode="HTML")
                except: pass
                break
    
    await del_user_msgs(user_id)
    p = players.get(user_id)
    if p and p.get("day", 0) > 0:
        await send_msg(user_id, f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n📅 День {p['day']} | 💰 {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="💎 РЕДКИЕ ТОВАРЫ", callback_data="action_rare")],
        ]))
    else:
        await send_msg(user_id, "🎮 <b>RESELL TYCOON</b>\n\nРедкие товары • Скины • Аукцион\n\n👇 Жми начать!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="💎 РЕДКИЕ ТОВАРЫ", callback_data="action_rare")],
        ]))

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, user_id))

# ==================== РЕДКИЕ ТОВАРЫ ====================
@dp.callback_query(F.data == "action_rare", StateFilter(GameState.playing))
async def show_rare_items(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    
    # Проверяем, не пора ли создать новый редкий товар
    has_new = check_rare_item_spawn()
    
    rare_item = rare_item_timer.get("current_item")
    if not rare_item:
        rare_item_timer["current_item"] = generate_rare_item()
        rare_item_timer["last_spawn"] = time_module.time()
        rare_item = rare_item_timer["current_item"]
    
    time_left = max(0, 180 - int(time_module.time() - rare_item_timer["last_spawn"]))
    mins, secs = divmod(time_left, 60)
    
    txt = (
        f"💎 <b>РЕДКИЕ ТОВАРЫ</b>\n\n"
        f"Текущий редкий товар:\n"
        f"📦 {rare_item['name']}\n"
        f"🔖 Редкость: {rare_item['rarity_name']}\n"
        f"💰 Цена: {rare_item['buy_price']}₽\n"
        f"📊 Рынок: ~{rare_item['market_price']}₽\n\n"
        f"⏳ Новый товар через: {mins}м {secs}с\n\n"
        f"<i>Редкие товары приносят больше прибыли!</i>"
    )
    
    kb = [
        [InlineKeyboardButton(text=f"🛒 КУПИТЬ ЗА {rare_item['buy_price']}₽", callback_data="buy_rare_item")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
    ]
    
    if p["balance"] < rare_item["buy_price"]:
        kb[0] = [InlineKeyboardButton(text=f"❌ НЕ ХВАТАЕТ (нужно {rare_item['buy_price']}₽)", callback_data="noop")]

    # Показываем редкости
    txt += "\n\n📊 <b>Шансы редкостей:</b>\n"
    for r_id, r_data in ITEM_RARITIES.items():
        txt += f"{r_data['color']} {r_data['name']}: {r_data['chance']}%\n"
    
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "buy_rare_item", StateFilter(GameState.playing))
async def buy_rare_item_btn(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    rare_item = rare_item_timer.get("current_item")
    
    if not rare_item:
        return await callback.answer("Нет доступного товара!")
    
    if p["balance"] < rare_item["buy_price"]:
        return await callback.answer("❌ Недостаточно денег!")
    
    # Покупаем
    p["balance"] -= rare_item["buy_price"]
    p["inventory"].append({
        "name": rare_item["name"],
        "cat": rare_item["cat"],
        "buy_price": rare_item["buy_price"],
        "market_price": rare_item["market_price"],
        "rarity": rare_item["rarity"]
    })
    
    # Сбрасываем таймер
    rare_item_timer["current_item"] = None
    rare_item_timer["last_spawn"] = time_module.time()
    
    await callback.answer(f"✅ Куплен {rare_item['rarity_name']} товар!")
    await send_msg(user_id, f"💎 <b>КУПЛЕН РЕДКИЙ ТОВАР!</b>\n\n📦 {rare_item['name']}\n🔖 {rare_item['rarity_name']}\n💰 Закуп: {rare_item['buy_price']}₽\n📊 Рынок: ~{rare_item['market_price']}₽\n\n👇 Зайди в 📦 ИНВЕНТАРЬ чтобы опубликовать!")

# ==================== СКИНЫ ====================
@dp.callback_query(F.data == "action_skins")
async def show_skins_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_skin = get_player_skin(user_id)
    p = get_player(user_id)
    
    txt = "👤 <b>МАГАЗИН СКИНОВ</b>\n\n"
    kb = []
    
    for skin in SKINS:
        owned = current_skin == skin["id"]
        if owned:
            txt += f"✅ {skin['emoji']} <b>{skin['name']}</b> ({skin['rarity']}) — ТВОЙ\n"
        else:
            if p["balance"] >= skin["price"]:
                kb.append([InlineKeyboardButton(text=f"{skin['emoji']} {skin['name']} ({skin['rarity']}) — {skin['price']}₽", callback_data=f"buy_skin_{skin['id']}")])
            else:
                txt += f"{skin['emoji']} {skin['name']} ({skin['rarity']}) — {skin['price']}₽ (не хватает)\n"
    
    kb.append([InlineKeyboardButton(text="🎨 КАСТОМИЗАЦИЯ", callback_data="action_avatar")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    config = get_current_avatar_config(user_id)
    try:
        msg = await bot.send_photo(user_id, get_avatar_url(config), caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await del_prev(user_id); last_bot_message[user_id] = msg.message_id
        try: await callback.message.delete()
        except: pass
    except:
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buy_skin_"))
async def buy_skin_btn(callback: CallbackQuery):
    success, msg = buy_skin(callback.from_user.id, callback.data.replace("buy_skin_", ""))
    if success: await callback.answer(msg); await show_skins_shop(callback)
    else: await callback.answer(msg, show_alert=True)

# ==================== МАГАЗИН ====================
@dp.callback_query(F.data == "action_shop", StateFilter(GameState.playing))
async def show_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(user_id)["level"]), SHOP_LEVELS[0])
    elapsed = time_module.time() - get_player_shop(user_id)["last_collect"]
    income = int(current_shop["income_per_hour"] * (elapsed / 3600))
    p = get_player(user_id)
    
    txt = f"🏪 <b>МАГАЗИН ОДЕЖДЫ</b>\n\nТвой: {current_shop['name']}\n💰 Доход: {current_shop['income_per_hour']}₽/час\n💵 Накоплено: {income}₽\n💼 Баланс: {p['balance']}₽"
    
    kb = []
    if income > 0: kb.append([InlineKeyboardButton(text=f"💰 СОБРАТЬ +{income}₽", callback_data="collect_shop_income")])
    
    for shop in SHOP_LEVELS:
        if shop["price"] > current_shop["price"] and p["balance"] >= shop["price"]:
            kb.append([InlineKeyboardButton(text=f"🛒 {shop['name']} — {shop['price']}₽", callback_data=f"buy_shop_{shop['id']}")])
    
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    if current_shop.get("image_url") and current_shop["image_url"].startswith("AgAC"):
        try:
            msg = await bot.send_photo(user_id, current_shop["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await del_prev(user_id); last_bot_message[user_id] = msg.message_id
            try: await callback.message.delete()
            except: pass
        except:
            await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
    user_id = callback.from_user.id
    active_items = [item for item in auction_data.get("items", []) if item.get("active", True)]
    
    txt = "🔨 <b>АУКЦИОН</b>\n\n"
    if not active_items:
        txt += "Нет активных лотов.\n\n<i>Выстави свой товар или скин!</i>"
        kb = [[InlineKeyboardButton(text="📤 ВЫСТАВИТЬ ЛОТ", callback_data="auction_sell")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]
        return await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    kb = []
    for i, item in enumerate(active_items):
        current_bid = item.get("current_bid", item["start_price"])
        time_left = max(0, int(item.get("end_time", 0) - time_module.time()))
        hours, mins = divmod(time_left, 3600)
        item_type = item.get("type", "item")
        txt += f"📦 <b>Лот #{i+1}:</b> {item['item']['name']}\n"
        txt += f"💰 Текущая: {current_bid}₽\n⏳ {int(hours)}ч {int(mins)}м\n\n"
        if item["seller_id"] != user_id:
            kb.append([InlineKeyboardButton(text=f"💰 СТАВКА (мин. {int(current_bid * 1.1)}₽)", callback_data=f"auction_bid_{i}")])
    
    kb.append([InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "auction_sell", StateFilter(GameState.playing))
async def auction_sell_menu(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    kb = []
    
    # Товары из инвентаря
    for i, item in enumerate(p["inventory"]):
        kb.append([InlineKeyboardButton(text=f"📦 {item['name']} (~{item['market_price']}₽)", callback_data=f"auction_put_{i}")])
    
    # Скины
    current_skin = get_player_skin(user_id)
    for skin in SKINS:
        if skin["id"] == current_skin and skin["id"] != "default":
            kb.append([InlineKeyboardButton(text=f"👤 Скин: {skin['name']} — {skin['price']}₽", callback_data=f"auction_skin_{skin['id']}")])
    
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_auction")])
    
    if not kb:
        return await callback.answer("Нечего выставить!")
    
    await edit_msg(callback.message, "📤 <b>ВЫСТАВИТЬ НА АУКЦИОН</b>\n\nВыбери товар или скин:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ==================== ОСНОВНОЙ ЧАТ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    # Продажа
    for w in ["продано", "продаю", "согласен", "договорились", "по рукам", "забирай", "отдаю", "продам", "бери", "ок", "давай"]:
        if w in text.lower():
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
    
    # Диалог
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
    
    if chat["round"] >= 5:
        chat["finished"] = True
        if random.random() < 0.6:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Ладно, давайте {chat['offer']}₽!")
            await complete_sale(user_id, chat["buyer_id"], message)
        else:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Извините, передумал.")
        return
    
    try:
        system_prompt = CLIENT_TYPES[chat["client_type"]]["system_prompt"] + f"\nТовар: {chat['item']}. Твоя цена: {chat['offer']}₽."
        resp = client_openai.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}] + chat["history"][-2:], temperature=0.7, max_tokens=80)
        ai_msg = resp.choices[0].message.content
    except:
        ai_msg = f"Ну так что? {chat['offer']}₽ — берёте?"
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    for w in ["беру", "договорились", "по рукам", "забираю", "согласен"]:
        if w in ai_msg.lower() and "?" not in ai_msg.lower():
            chat["finished"] = True
            if user_id in active_chat_for_user: del active_chat_for_user[user_id]
            await complete_sale(user_id, chat["buyer_id"], message)
            return
    
    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}")

# ==================== ОСТАЛЬНЫЕ CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_list = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    if not active_list:
        return await edit_msg(callback.message, "💬 Нет активных диалогов.")
    txt = f"💬 <b>ДИАЛОГИ ({len(active_list)}):</b>\n\n"
    kb = []
    for key, chat in active_list:
        txt += f"👤 #{chat['buyer_id']} | {chat['item']} | {chat['offer']}₽\n"
        kb.append([InlineKeyboardButton(text=f"💬 Ответить #{chat['buyer_id']}", callback_data=f"open_chat_{user_id}_{chat['buyer_id']}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("open_chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[2]); buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    if chat_key not in active_chats or active_chats[chat_key]["finished"]: return await callback.answer("Диалог завершён")
    active_chat_for_user[user_id] = chat_key
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"💬 <b>ДИАЛОГ #{buyer_id}</b>\nНапиши ответ или «продано»!")

@dp.callback_query(F.data == "action_leaderboard", StateFilter(GameState.playing))
async def show_leaderboard(callback: CallbackQuery):
    top = get_top_players(10)
    if not top: return await edit_msg(callback.message, "🏆 Пока нет данных.")
    txt = "🏆 <b>ТОП-10 ПРОДАВЦОВ</b>\n\n"
    for i, (uid, profit, sales) in enumerate(top):
        try: name = (await bot.get_chat(uid)).first_name or f"ID:{uid}"
        except: name = f"ID:{uid}"
        txt += f"{['🥇','🥈','🥉'][i] if i<3 else f'{i+1}.'} {name} — {profit}₽\n"
    await edit_msg(callback.message, txt)

@dp.callback_query(F.data == "action_houses", StateFilter(GameState.playing))
async def show_houses_catalog(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id; current_id = get_player_house(user_id); p = get_player(user_id)
    if page < 0: page = 0
    if page >= len(HOUSES): page = len(HOUSES) - 1
    house = HOUSES[page]; owned = current_id == house["id"]
    status_text = "✅ ТВОЁ" if owned else (f"💰 {house['price']}₽ (хватает!)" if p["balance"] >= house["price"] else f"💰 {house['price']}₽ (не хватает)")
    action_btn = InlineKeyboardButton("🛒 КУПИТЬ", callback_data=f"buy_house_{house['id']}") if not owned and p["balance"] >= house["price"] else None
    
    txt = f"🏠 <b>НЕДВИЖИМОСТЬ</b> {page+1}/{len(HOUSES)}\n\n{house['name']}\n{house['description']}\n{status_text}"
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"house_page_{page-1}"))
    if page < len(HOUSES)-1: nav.append(InlineKeyboardButton("➡️", callback_data=f"house_page_{page+1}"))
    kb = []
    if nav: kb.append(nav)
    if action_btn: kb.append([action_btn])
    kb.append([InlineKeyboardButton("🏠 В МЕНЮ", callback_data="action_back")])
    
    try:
        if house["image_url"].startswith("AgAC"):
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await del_prev(user_id); last_bot_message[user_id] = msg.message_id
            try: await callback.message.delete()
            except: pass
        else:
            await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except:
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("house_page_"), StateFilter(GameState.playing))
async def house_page_btn(callback: CallbackQuery):
    await show_houses_catalog(callback, int(callback.data.split("_")[2]))

@dp.callback_query(F.data.startswith("buy_house_"), StateFilter(GameState.playing))
async def buy_house_btn(callback: CallbackQuery):
    success, msg = buy_house(callback.from_user.id, callback.data.replace("buy_house_", ""))
    if success: await callback.answer(msg); await show_houses_catalog(callback)
    else: await callback.answer(msg, show_alert=True)

# ==================== АВАТАР ====================
@dp.callback_query(F.data == "action_avatar")
async def show_avatar_menu_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    config = get_current_avatar_config(user_id)
    kb = []
    for part_key, part_data in AVATAR_PARTS.items():
        current_value = config.get(part_key, "default")
        kb.append([InlineKeyboardButton(text=f"{part_data['name']}: {part_data['options'].get(current_value, current_value)}", callback_data=f"avatar_part_{part_key}")])
    kb.append([InlineKeyboardButton(text="👤 К СКИНАМ", callback_data="action_skins")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ" if players.get(user_id, {}).get("day", 0) > 0 else "🏠 НА ГЛАВНУЮ", callback_data="action_back" if players.get(user_id, {}).get("day", 0) > 0 else "back_to_start")])
    try:
        msg = await bot.send_photo(user_id, get_avatar_url(config), caption="👤 <b>КАСТОМИЗАЦИЯ</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await del_prev(user_id); last_bot_message[user_id] = msg.message_id
        try: await callback.message.delete()
        except: pass
    except:
        await edit_msg(callback.message, "👤 <b>КАСТОМИЗАЦИЯ</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("avatar_part_"))
async def show_avatar_options(callback: CallbackQuery):
    part_key = callback.data.replace("avatar_part_", "")
    part_data = AVATAR_PARTS.get(part_key)
    if not part_data: return await callback.answer("Ошибка!")
    config = get_current_avatar_config(callback.from_user.id)
    kb = []
    for opt_key, opt_name in part_data["options"].items():
        selected = "✅ " if config.get(part_key) == opt_key else ""
        kb.append([InlineKeyboardButton(text=f"{selected}{opt_name}", callback_data=f"set_avatar_{part_key}_{opt_key}")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_avatar")])
    await edit_msg(callback.message, f"👤 <b>{part_data['name'].upper()}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("set_avatar_"))
async def set_avatar_part(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) >= 4:
        part_key = parts[2]; opt_key = "_".join(parts[3:])
        if part_key in AVATAR_PARTS and opt_key in AVATAR_PARTS[part_key]["options"]:
            update_avatar_part(callback.from_user.id, part_key, opt_key)
            await callback.answer("✅ Обновлено!"); await show_avatar_options(callback)

# ==================== ПУБЛИКАЦИЯ ====================
@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    item = p["inventory"][item_idx]
    await state.set_state(GameState.writing_description)
    await state.update_data(publish_item_idx=item_idx)
    await send_msg(user_id, f"✍️ <b>ОПИШИ ТОВАР</b>\n\n📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n\nНапиши описание в чат.")

@dp.message(StateFilter(GameState.writing_description))
async def handle_description(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; description = message.text.strip()
    data = await state.get_data(); item_idx = data.get("publish_item_idx", 0)
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): await state.set_state(GameState.playing); return
    item = p["inventory"][item_idx]
    quality = rate_description(description)
    if user_id not in item_descriptions: item_descriptions[user_id] = {}
    item_descriptions[user_id][item["name"]] = {"description": description, "quality": quality}
    published_items[user_id] = {"item": item.copy()}
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"📢 <b>ОПУБЛИКОВАНО!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n📝 Качество: {get_quality_bonus(quality)['name']} ({quality}/10)\n⏳ Жди 1-3 минуты!")
    asyncio.create_task(spawn_buyers(user_id))

# ==================== ПОДРАБОТКИ ====================
async def job_animation(user_id, job_idx):
    job = JOBS[job_idx]; interval = job["duration"] / len(job["steps"])
    for i in range(len(job["steps"])):
        await asyncio.sleep(interval)
        if user_id not in side_jobs or side_jobs[user_id].get("done", True): return
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        side_jobs[user_id]["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]
        await send_msg(user_id, f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n💰 +{job['reward']}₽")

@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    kb = [[InlineKeyboardButton(text=f"{j['emoji']} {j['name']} — {j['reward']}₽", callback_data=f"start_job_{i}")] for i, j in enumerate(JOBS)]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "💼 <b>ПОДРАБОТКИ</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("start_job_"))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id; job_idx = int(callback.data.split("_")[2])
    side_jobs[user_id] = {"job_type": job_idx, "start_time": time_module.time(), "done": False}
    await send_msg(user_id, f"💼 <b>ПРИСТУПИЛ!</b>\n{JOBS[job_idx]['emoji']} {JOBS[job_idx]['name']}\n💰 {JOBS[job_idx]['reward']}₽")
    asyncio.create_task(job_animation(user_id, job_idx))

# ==================== ОБЩИЕ CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "menu_page_1")
async def menu_page_1(callback: CallbackQuery):
    await edit_msg(callback.message, "📅 <b>МЕНЮ — СТРАНИЦА 1/2</b>", reply_markup=main_kb(1, callback.from_user.id))

@dp.callback_query(F.data == "menu_page_2")
async def menu_page_2(callback: CallbackQuery):
    await edit_msg(callback.message, "📅 <b>МЕНЮ — СТРАНИЦА 2/2</b>", reply_markup=main_kb(2, callback.from_user.id))

@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    await state.set_state(GameState.playing)
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n💰 5 000₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(players[user_id])}", reply_markup=main_kb(1, user_id))

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    p = players.get(callback.from_user.id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽", reply_markup=main_kb(1, callback.from_user.id))

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(callback.from_user.id)), HOUSES[0])
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(callback.from_user.id)["level"]), SHOP_LEVELS[0])
    await edit_msg(callback.message, f"📊 <b>СТАТИСТИКА:</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n🏠 {house['name']}\n🏪 {shop['name']}")

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    await edit_msg(callback.message, f"📊 <b>РЫНОК</b>\n\n{fmt_demand(get_player(callback.from_user.id))}")

@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu_callback(callback: CallbackQuery):
    u = get_rep(callback.from_user.id)
    await edit_msg(callback.message, f"🏅 <b>РЕПУТАЦИЯ: {rep_level(u['score'])}</b>\n📊 {u['score']}/100\n📦 Продаж: {u['total_sales']}\n💰 Прибыль: {u['total_profit']}₽")

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await edit_msg(callback.message, f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{ref_link(user_id)}</code>\n\n💰 +500₽ за друга")

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id; supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = [[InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"sup_{supps.index(s)}")] for s in supps]
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, f"🏭 <b>ПОСТАВЩИКИ</b>{' 👑 VIP!' if is_vip(user_id) else ''}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sup_"), StateFilter(GameState.playing))
async def show_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]; items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    p = get_player(user_id)
    kb = [[InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {int(item_price(it['base_price'], sup) * rep_mult(get_rep(user_id)['score'])['supplier_discount'])}₽", callback_data=f"bi_{i}")] for i, it in enumerate(items)]
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data=f"sup_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 К ПОСТАВЩИКАМ", callback_data="action_buy")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await state.update_data(sup_idx=idx, sup_items=items)
    await edit_msg(callback.message, f"{sup['emoji']} <b>{sup['name']}</b>\n⭐ {sup['rating']}/10 | ⚠️ Кид:{sup['scam_chance']}%\n\nВыбери товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("bi_"), StateFilter(GameState.playing))
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1]); sup_idx = data.get("sup_idx", 0)
    items = data.get("sup_items", []); user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[sup_idx]
    if item_idx >= len(items): return await callback.answer("Ошибка")
    item = items[item_idx]; p = get_player(user_id)
    price = int(item_price(item["base_price"], sup) * rep_mult(get_rep(user_id)["score"])["supplier_discount"])
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    if random.randint(1, 100) <= int(sup["scam_chance"] * rep_mult(get_rep(user_id)["score"])["scam_reduce"]):
        p["balance"] -= price; add_rep(user_id, -5)
        await edit_msg(callback.message, f"💀 <b>КИНУЛИ!</b>\n-{price}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
        return
    p["balance"] -= price
    mp = market_price(item["base_price"], p["market_demand"].get(item["cat"], 1.0))
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": mp})
    await edit_msg(callback.message, f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽ | Рынок: ~{mp}₽\n\n👇 📦 ИНВЕНТАРЬ → Опубликовать!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")]]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    if not p["inventory"]: return await edit_msg(callback.message, "📦 <b>ПУСТО</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")]]))
    kb = [[InlineKeyboardButton(text=f"{it['name']} | {it['buy_price']}₽ → ~{it['market_price']}₽", callback_data=f"inv_{i}")] for i, it in enumerate(p["inventory"])]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "📦 <b>ИНВЕНТАРЬ</b>\n\n" + "\n".join(f"{i+1}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"])) + "\n\n👇 Нажми чтобы опубликовать!", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    bonus = house["income_bonus"]
    shop_income = collect_shop_income(user_id)
    p["balance"] += bonus; p["day"] += 1
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    if user_id in published_items: published_items[user_id] = None
    sold_items[user_id].clear()
    await edit_msg(callback.message, f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽\n🏠 +{bonus}₽{f' | 🏪 +{shop_income}₽' if shop_income > 0 else ''}", reply_markup=main_kb(1, user_id))

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    p = get_player(callback.from_user.id); await state.clear()
    r = "🏆 <b>ПОБЕДА!</b>" if p["balance"] >= 50000 else "💀 <b>БАНКРОТ!</b>" if p["balance"] <= 0 else "🎮 Игра окончена."
    await edit_msg(callback.message, f"{r}\n💰 {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, callback.from_user.id))

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    await edit_msg(callback.message, "🎮 <b>RESELL TYCOON</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")]]))

# ==================== ПОЛУЧЕНИЕ ССЫЛОК НА ФОТО ====================
@dp.message(F.photo)
async def get_photo_links(message: types.Message):
    photo = message.photo[-1]; file_id = photo.file_id
    file = await bot.get_file(file_id)
    await message.answer(f"✅ <b>ID:</b>\n<code>{file_id}</code>", parse_mode="HTML")

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon + Редкие товары запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())