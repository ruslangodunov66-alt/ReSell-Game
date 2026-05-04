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
SHOPS_FILE = "player_shops.json"
AUCTION_FILE = "auction_data.json"
LEADERBOARD_FILE = "leaderboard.json"
SKINS_FILE = "player_skins.json"
SUPPLIER_ITEMS_FILE = "supplier_items.json"

# ==================== СКИНЫ ====================
SKINS = [
    {"id": "default", "name": "Новичок", "price": 0, "rarity": "common", "rep_required": 0, "emoji": "👶", "avatar_config": {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}, "image_url": "AgACAgIAAxkBAAIDHGn4w7w3AAGnzzdBPwI4mNZEgoIjsAACzhhrG8bbwEsN1TBcMS6PhwEAAwIAA3kAAzsE"},
    {"id": "hustler", "name": "Темщик", "price": 0, "rarity": "common", "rep_required": 25, "emoji": "😎", "avatar_config": {"face": "cool", "hair": "mohawk", "clothes": "jacket", "accessory": "sunglasses", "background": "gray"}, "image_url": "AgACAgIAAxkBAAIDLGn4xLrV_G5vUn9b0lfZbRt9uSNpAAIjE2sbRxXIS2ta2c2uvaRDAQADAgADeQADOwQ"},
    {"id": "boss", "name": "Мажор", "price": 0, "rarity": "common", "rep_required": 50, "emoji": "🕴", "avatar_config": {"face": "cool", "hair": "short", "clothes": "suit", "accessory": "glasses", "background": "blue"}, "image_url": "AgACAgIAAxkBAAIDIGn4w8SxLumhkkue8rlTXiUqetBaAALQGGsbxtvAS3sUKevJKpGYAQADAgADeQADOwQ"},
    {"id": "coffee", "name": "Кофейный барыга", "price": 25000, "rarity": "rare", "rep_required": 0, "emoji": "💻", "avatar_config": {"face": "smile", "hair": "cap", "clothes": "rich", "accessory": "chain", "background": "purple"}, "image_url": "AgACAgIAAxkBAAIDImn4w8m4lmlm6AYS1kBkt8Dx7ZyXAAL9GGsbxtvAS_vggWeGPBAgAQADAgADeQADOwQ"},
    {"id": "legend", "name": "Бог товарки", "price": 50000, "rarity": "legendary", "rep_required": 0, "emoji": "👑", "avatar_config": {"face": "cool", "hair": "long", "clothes": "rich", "accessory": "headphones", "background": "green"}, "image_url": "AgACAgIAAxkBAAIDJGn4w8wheVk6HY-7qpII5w8hQ4lyAAL_GGsbxtvAS2S7TonuV3alAQADAgADeQADOwQ"},
    {"id": "gold", "name": "Золотой барыга", "price": 150000, "rarity": "legendary", "rep_required": 0, "emoji": "🥇", "avatar_config": {"face": "cool", "hair": "cap", "clothes": "rich", "accessory": "chain", "background": "purple"}, "image_url": "AgACAgIAAxkBAAIDJmn4w8_mwnpx1Ms388hYBj68KUW2AAMZaxvG28BLntt7LmTTjtwBAAMCAAN5AAM7BA"},
]

# ==================== ОБЩИЕ ТОВАРЫ ====================
SUPPLIER_ITEM_RARITIES = {
    "common": {"name": "Обычный", "color": "⬜", "price_mult_min": 0.8, "price_mult_max": 1.3, "chance": 55},
    "rare": {"name": "Редкий", "color": "🟦", "price_mult_min": 1.5, "price_mult_max": 2.5, "chance": 25},
    "epic": {"name": "Эпик", "color": "🟪", "price_mult_min": 2.5, "price_mult_max": 5.0, "chance": 12},
    "legendary": {"name": "Легендарный", "color": "🟨", "price_mult_min": 5.0, "price_mult_max": 12.0, "chance": 6},
    "mythic": {"name": "Мифик", "color": "🟥", "price_mult_min": 10.0, "price_mult_max": 30.0, "chance": 2},
}

supplier_stock = {"items": [], "last_update": 0}

def generate_supplier_items():
    items = []
    count = random.randint(6, 10)
    for _ in range(count):
        rarities = list(SUPPLIER_ITEM_RARITIES.keys())
        weights = [SUPPLIER_ITEM_RARITIES[r]["chance"] for r in rarities]
        rarity = random.choices(rarities, weights=weights, k=1)[0]
        rarity_data = SUPPLIER_ITEM_RARITIES[rarity]
        base_item = random.choice(BASE_ITEMS)
        price_mult = random.uniform(rarity_data["price_mult_min"], rarity_data["price_mult_max"])
        market_price = int(base_item["base_price"] * price_mult)
        buy_price = int(market_price * random.uniform(0.6, 0.85))
        end_time = time_module.time() + random.randint(300, 900)
        items.append({
            "name": f"{rarity_data['color']} {base_item['cat']} {base_item['name']}",
            "cat": base_item["cat"], "buy_price": buy_price, "market_price": market_price,
            "rarity": rarity, "rarity_name": rarity_data["name"], "rarity_color": rarity_data["color"],
            "end_time": end_time, "id": random.randint(10000, 99999)
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

CLIENT_TYPES = {
    "angry": {"system_prompt": "Ты покупатель. Торгуешься. 1-3 предложения.", "discount_range": (0.6, 0.8), "patience": 4},
    "kind": {"system_prompt": "Ты покупатель. Вежливый. 1-3 предложения.", "discount_range": (0.85, 0.95), "patience": 6},
    "sly": {"system_prompt": "Ты перекупщик. 1-3 предложения.", "discount_range": (0.7, 0.85), "patience": 5},
}

JOBS = [
    {"id": "flyers", "name": "📦 Расклейка", "duration": 60, "reward": 200, "emoji": "📦"},
    {"id": "delivery", "name": "🚗 Доставка", "duration": 120, "reward": 500, "emoji": "🚗"},
    {"id": "freelance", "name": "💻 Фриланс", "duration": 300, "reward": 1200, "emoji": "💻"},
]

HOUSES = [
    {"id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0, "image_url": ""},
    {"id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150, "image_url": ""},
    {"id": "house", "name": "🏠 Дом", "price": 35000, "income_bonus": 400, "image_url": ""},
    {"id": "villa", "name": "🏰 Вилла", "price": 100000, "income_bonus": 1200, "image_url": ""},
    {"id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000, "image_url": ""},
]

SHOP_LEVELS = [
    {"id": "none", "name": "Нет магазина", "price": 0, "income_per_hour": 0, "image_url": ""},
    {"id": "stall", "name": "🛍 Лавка", "price": 5000, "income_per_hour": 100, "image_url": ""},
    {"id": "container", "name": "📦 Контейнер", "price": 15000, "income_per_hour": 300, "image_url": ""},
    {"id": "store", "name": "🏬 Магазин", "price": 50000, "income_per_hour": 800, "image_url": ""},
    {"id": "boutique", "name": "👑 Бутик", "price": 150000, "income_per_hour": 2000, "image_url": ""},
]

REPUTATION_LEVELS = {-100: "💀 ЧС", -50: "🔴 Ужасная", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 75: "🟣 Легенда", 100: "👑 Бог товарки"}
LESSONS = [{"id": 1, "title": "🚀 Основы", "text": "📚 Основы товарки", "reward": 500}, {"id": 2, "title": "📊 Рынок", "text": "📚 Анализ рынка", "reward": 500}]

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
player_houses = {}
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
    global referral_data, rep_data, learning_data, player_houses, player_shops, player_skins, auction_data, leaderboard_data, supplier_stock
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})
    player_houses = load_json(HOUSES_FILE, {})
    player_shops = load_json(SHOPS_FILE, {})
    player_skins = load_json(SKINS_FILE, {})
    auction_data = load_json(AUCTION_FILE, {"items": []})
    leaderboard_data = load_json(LEADERBOARD_FILE, {})
    supplier_stock = load_json(SUPPLIER_ITEMS_FILE, {"items": [], "last_update": 0})

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

async def edit_msg(message, text, parse_mode="HTML", reply_markup=None):
    await del_user_msgs(message.chat.id)
    try: await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        print(f"Edit error: {e}")
        # Отправляем новое сообщение если не можем отредактировать
        await send_msg(message.chat.id, text, parse_mode=parse_mode, reply_markup=reply_markup)

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
    if uid not in rep_data: rep_data[uid] = {"score": 0, "total_sales": 0, "total_profit": 0, "achievements": []}
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
    if get_player_skin(user_id) == skin_id: return False, "Уже есть!"
    p = get_player(user_id)
    if skin["price"] > 0 and p["balance"] < skin["price"]: return False, "Недостаточно!"
    if skin["price"] > 0: p["balance"] -= skin["price"]
    player_skins[str(user_id)] = skin_id
    save_json(SKINS_FILE, player_skins)
    return True, f"✅ {skin['name']}!"

def check_rep_skins(user_id):
    rep_score = get_rep(user_id)["score"]
    return [s for s in SKINS if s["rep_required"] > 0 and rep_score >= s["rep_required"] and get_player_skin(user_id) != s["id"]]

def get_avatar_url(avatar_config):
    return f"https://api.dicebear.com/7.x/pixel-art/svg?seed={hashlib.md5(str(avatar_config).encode()).hexdigest()[:10]}"

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

# ==================== МЕНЮ ====================
def main_kb(page=1, user_id=None):
    if page == 1:
        bc = get_active_buyers_count(user_id) if user_id else 0
        chat_label = f"💬 ЧАТЫ ({bc})" if bc > 0 else "💬 ЧАТЫ"
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="action_buy"),
             InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
            [InlineKeyboardButton(text=chat_label, callback_data="action_chats"),
             InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="action_auction")],
            [InlineKeyboardButton(text="💼 РАБОТА", callback_data="action_job"),
             InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand")],
            [InlineKeyboardButton(text="⏩ ДЕНЬ ВПЕРЁД", callback_data="action_nextday")],
            [InlineKeyboardButton(text="➡️ ВКЛАДКА 2", callback_data="menu_page_2")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 ЖИЛЬЁ", callback_data="action_houses"),
             InlineKeyboardButton(text="🏪 МАГАЗИН", callback_data="action_shop")],
            [InlineKeyboardButton(text="👤 СКИНЫ", callback_data="action_skins")],
            [InlineKeyboardButton(text="🏆 ЛИДЕРЫ", callback_data="action_leaderboard")],
            [InlineKeyboardButton(text="📊 СТАТЫ", callback_data="action_stats"),
             InlineKeyboardButton(text="🏅 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
            [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
            [InlineKeyboardButton(text="⬅️ ВКЛАДКА 1", callback_data="menu_page_1"),
             InlineKeyboardButton(text="🏁 КОНЕЦ", callback_data="action_end")],
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
    if q >= 9: return {"name": "🔥", "buyers_bonus": 3}
    elif q >= 7: return {"name": "⭐", "buyers_bonus": 2}
    elif q >= 5: return {"name": "👍", "buyers_bonus": 1}
    return {"name": "👌", "buyers_bonus": 0}

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
        discount = random.uniform(*client["discount_range"])
        discount = max(0.3, min(0.95, discount))
        offer = int(price * discount); offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        msg = first_msg(client_type, item_name, price, offer)
        active_chats[chat_key] = {"user_id": user_id, "buyer_id": buyer_id, "client_type": client_type, "item": item_name, "price": price, "offer": offer, "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}], "round": 1, "max_rounds": client["patience"], "finished": False}
        await send_msg(user_id, f"📩 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n💬 {msg}")
    else:
        chat = active_chats.get(chat_key)
        if chat and not chat["finished"]:
            chat["history"].append({"role": "assistant", "content": f"Жду ответ по {item_name}."})
            await send_msg(user_id, f"🔔 <b>Покупатель #{buyer_id}</b>")

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
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
    
    # Обработка рефералов
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
    
    # Проверяем скины за репутацию
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
    
    # Отправляем фото скина
    if skin.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, skin["image_url"], caption=txt, parse_mode="HTML", reply_markup=kb)
            last_bot_message[user_id] = msg.message_id
        except:
            await send_msg(user_id, txt, reply_markup=kb)
    else:
        await send_msg(user_id, txt, reply_markup=kb)

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
    await send_msg(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, user_id))

# ==================== ЧАТ С ПОКУПАТЕЛЯМИ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    if not message.text: return
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
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Ладно, {chat['offer']}₽!")
            await complete_sale(user_id, chat["buyer_id"], message)
        else:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Извините, передумал.")
        return
    
    try:
        system_prompt = CLIENT_TYPES[chat["client_type"]]["system_prompt"] + f"\nТовар: {chat['item']}. Твоя цена: {chat['offer']}₽."
        resp = client_openai.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}] + chat["history"][-2:], temperature=0.7, max_tokens=80)
        ai_msg = resp.choices[0].message.content
    except:
        ai_msg = f"Ну так что? {chat['offer']}₽?"
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    for w in ["беру", "договорились", "по рукам", "забираю", "согласен"]:
        if w in ai_msg.lower() and "?" not in ai_msg.lower():
            chat["finished"] = True
            if user_id in active_chat_for_user: del active_chat_for_user[user_id]
            await complete_sale(user_id, chat["buyer_id"], message)
            return
    
    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}")

# ==================== ЧАТЫ ====================
@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_list = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    if not active_list:
        return await edit_msg(callback.message, "💬 Нет диалогов.\nОпубликуй товар в 📦 Инвентаре!")
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
    await send_msg(user_id, f"💬 <b>ДИАЛОГ #{buyer_id}</b>\nПиши «продано» чтобы продать!")

# ==================== СКИНЫ ====================
@dp.callback_query(F.data == "action_skins")
async def show_skins_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_skin = get_player_skin(user_id)
    p = get_player(user_id)
    rep_score = get_rep(user_id)["score"]
    
    txt = f"👤 <b>СКИНЫ</b>\n⭐ Репутация: {rep_score}/100 ({rep_level(rep_score)})\n💼 Баланс: {p['balance']}₽\n\n"
    txt += "<b>Бесплатные (за репутацию):</b>\n"
    kb = []
    
    for skin in SKINS:
        owned = current_skin == skin["id"]
        if owned:
            txt += f"✅ {skin['emoji']} {skin['name']} — ТВОЙ\n"
        elif skin["rep_required"] > 0:
            if rep_score >= skin["rep_required"]:
                txt += f"🎁 {skin['emoji']} {skin['name']} — ДОСТУПЕН!\n"
                kb.append([InlineKeyboardButton(text=f"🎁 {skin['emoji']} {skin['name']} — ПОЛУЧИТЬ", callback_data=f"buy_skin_{skin['id']}")])
            else:
                txt += f"🔒 {skin['emoji']} {skin['name']} — нужно {skin['rep_required']} реп.\n"
    
    txt += "\n<b>Платные:</b>\n"
    for skin in SKINS:
        owned = current_skin == skin["id"]
        if skin["rep_required"] == 0 and skin["price"] > 0:
            if owned:
                txt += f"✅ {skin['emoji']} {skin['name']} — ТВОЙ\n"
            elif p["balance"] >= skin["price"]:
                kb.append([InlineKeyboardButton(text=f"💰 {skin['emoji']} {skin['name']} — {skin['price']}₽", callback_data=f"buy_skin_{skin['id']}")])
            else:
                txt += f"❌ {skin['emoji']} {skin['name']} — {skin['price']}₽\n"
    
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    current_skin_data = next((s for s in SKINS if s["id"] == current_skin), SKINS[0])
    if current_skin_data.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, current_skin_data["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await del_prev(user_id); last_bot_message[user_id] = msg.message_id
            try: await callback.message.delete()
            except: pass
        except:
            await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buy_skin_"))
async def buy_skin_btn(callback: CallbackQuery):
    user_id = callback.from_user.id; skin_id = callback.data.replace("buy_skin_", "")
    skin = next((s for s in SKINS if s["id"] == skin_id), None)
    if not skin: return await callback.answer("Не найден")
    if skin["rep_required"] > 0 and get_rep(user_id)["score"] < skin["rep_required"]:
        return await callback.answer(f"Нужно {skin['rep_required']} репутации!")
    success, msg = buy_skin(user_id, skin_id)
    if success: await callback.answer(msg); await show_skins_shop(callback)
    else: await callback.answer(msg, show_alert=True)

# ==================== ЗАКУПКА ====================
@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id
    check_supplier_update()
    items = supplier_stock.get("items", [])
    if not items: generate_supplier_items(); items = supplier_stock.get("items", [])
    
    txt = "🏭 <b>ПОСТАВЩИКИ</b>\n<i>Обновление каждые 5 мин.</i>\n\n"
    kb = []
    p = get_player(user_id)
    
    for item in items[:8]:
        time_left = max(0, int(item["end_time"] - time_module.time()))
        mins = time_left // 60
        txt += f"{item['rarity_color']} {item['name']} — {item['buy_price']}₽ ({mins}м)\n"
        if p["balance"] >= item["buy_price"]:
            kb.append([InlineKeyboardButton(text=f"{item['rarity_color']} {item['name']} — {item['buy_price']}₽", callback_data=f"buy_supplier_{item['id']}")])
    
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data="action_buy")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
    
    await callback.answer(f"✅ Куплен!")
    await send_msg(user_id, f"🛒 <b>КУПЛЕНО!</b>\n📦 {item['name']}\n💰 Закуп: {item['buy_price']}₽\n📊 Рынок: ~{item['market_price']}₽\n👇 📦 Инвентарь → Опубликовать!")

# ==================== МАГАЗИН ====================
@dp.callback_query(F.data == "action_shop", StateFilter(GameState.playing))
async def show_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(user_id)["level"]), SHOP_LEVELS[0])
    elapsed = time_module.time() - get_player_shop(user_id)["last_collect"]
    income = int(shop["income_per_hour"] * (elapsed / 3600))
    p = get_player(user_id)
    
    txt = f"🏪 <b>МАГАЗИН</b>\n\nТвой: {shop['name']}\n💰 Доход: {shop['income_per_hour']}₽/час\n💵 Накоплено: {income}₽\n💼 Баланс: {p['balance']}₽"
    kb = []
    if income > 0: kb.append([InlineKeyboardButton(text=f"💰 СОБРАТЬ +{income}₽", callback_data="collect_shop_income")])
    for s in SHOP_LEVELS:
        if s["price"] > shop["price"] and p["balance"] >= s["price"]:
            kb.append([InlineKeyboardButton(text=f"🛒 {s['name']} — {s['price']}₽", callback_data=f"buy_shop_{s['id']}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    if shop.get("image_url"):
        try:
            msg = await bot.send_photo(user_id, shop["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
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
    active_items = [item for item in auction_data.get("items", []) if item.get("active", True)]
    if not active_items:
        return await edit_msg(callback.message, "🔨 <b>АУКЦИОН</b>\n\nНет лотов.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    txt = "🔨 <b>АУКЦИОН</b>\n\n"
    kb = []
    for i, item in enumerate(active_items):
        time_left = max(0, int(item.get("end_time", 0) - time_module.time()))
        hours, mins = divmod(time_left, 3600)
        txt += f"📦 Лот #{i+1}: {item['item']['name']}\n💰 {item.get('current_bid', item['start_price'])}₽\n⏳ {int(hours)}ч {int(mins)}м\n\n"
        if item["seller_id"] != callback.from_user.id:
            kb.append([InlineKeyboardButton(text=f"💰 СТАВКА (мин. {int(item.get('current_bid', item['start_price']) * 1.1)}₽)", callback_data=f"auction_bid_{i}")])
    kb.append([InlineKeyboardButton(text="📤 ВЫСТАВИТЬ", callback_data="auction_sell")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "auction_sell", StateFilter(GameState.playing))
async def auction_sell_menu(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    kb = [[InlineKeyboardButton(text=f"📦 {item['name']} (~{item['market_price']}₽)", callback_data=f"auction_put_{i}")] for i, item in enumerate(p["inventory"])]
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_auction")])
    if not kb: return await callback.answer("Нечего выставить!")
    await edit_msg(callback.message, "📤 <b>ВЫСТАВИТЬ НА АУКЦИОН</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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

# ==================== ПОДРАБОТКИ ====================
@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    kb = [[InlineKeyboardButton(text=f"{j['emoji']} {j['name']} — {j['reward']}₽ ({j['duration']}с)", callback_data=f"start_job_{i}")] for i, j in enumerate(JOBS)]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "💼 <b>ПОДРАБОТКИ</b>\n\nВыбери работу:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("start_job_"))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id; job_idx = int(callback.data.split("_")[2])
    job = JOBS[job_idx]
    side_jobs[user_id] = {"job_type": job_idx, "start_time": time_module.time(), "done": False}
    await send_msg(user_id, f"💼 <b>РАБОТАЕМ!</b>\n{job['emoji']} {job['name']}\n💰 {job['reward']}₽\n⏱ {job['duration']} сек.")
    await callback.answer("Приступил!")
    asyncio.create_task(finish_job(user_id, job_idx))

async def finish_job(user_id, job_idx):
    await asyncio.sleep(JOBS[job_idx]["duration"])
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        side_jobs[user_id]["done"] = True
        if user_id in players: players[user_id]["balance"] += JOBS[job_idx]["reward"]
        try: await send_msg(user_id, f"✅ <b>ГОТОВО!</b>\n💰 +{JOBS[job_idx]['reward']}₽\n💼 Баланс: {players[user_id]['balance']}₽")
        except: pass

# ==================== ОСТАЛЬНЫЕ CALLBACK ====================
@dp.callback_query(F.data == "action_leaderboard", StateFilter(GameState.playing))
async def show_leaderboard(callback: CallbackQuery):
    top = get_top_players(10)
    if not top: return await edit_msg(callback.message, "🏆 Пока нет данных.")
    txt = "🏆 <b>ТОП-10 ПРОДАВЦОВ</b>\n\n"
    for i, (uid, profit, sales) in enumerate(top):
        try: name = (await bot.get_chat(uid)).first_name or f"ID:{uid}"
        except: name = f"ID:{uid}"
        txt += f"{['🥇','🥈','🥉'][i] if i<3 else f'{i+1}.'} {name} — {profit}₽\n"
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_houses", StateFilter(GameState.playing))
async def show_houses_catalog(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id; current_id = get_player_house(user_id); p = get_player(user_id)
    if page < 0: page = 0
    if page >= len(HOUSES): page = len(HOUSES) - 1
    house = HOUSES[page]; owned = current_id == house["id"]
    status_text = "✅ ТВОЁ" if owned else (f"💰 {house['price']}₽" if p["balance"] >= house["price"] else f"💰 {house['price']}₽ (не хватает)")
    action_btn = InlineKeyboardButton("🛒 КУПИТЬ", callback_data=f"buy_house_{house['id']}") if not owned and p["balance"] >= house["price"] else None
    txt = f"🏠 <b>ЖИЛЬЁ</b> {page+1}/{len(HOUSES)}\n\n{house['name']}\n{status_text}"
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"house_page_{page-1}"))
    if page < len(HOUSES)-1: nav.append(InlineKeyboardButton("➡️", callback_data=f"house_page_{page+1}"))
    kb = []
    if nav: kb.append(nav)
    if action_btn: kb.append([action_btn])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
    await edit_msg(callback.message, "📅 <b>МЕНЮ 1/2</b>", reply_markup=main_kb(1, callback.from_user.id))

@dp.callback_query(F.data == "menu_page_2")
async def menu_page_2(callback: CallbackQuery):
    await edit_msg(callback.message, "📅 <b>МЕНЮ 2/2</b>", reply_markup=main_kb(2, callback.from_user.id))

@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n💰 5 000₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, user_id))

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = players.get(user_id)
    
    if not p:
        # Создаём новую игру если нет
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
        p = players[user_id]
        event = daily_event(); p["current_event"] = event
        if event: apply_event(p, event)
    
    await state.set_state(GameState.playing)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, user_id))
    await callback.answer("Продолжаем! 🎮")

@dp.callback_query(F.data == "restart_game_confirm")
async def restart_confirm(callback: CallbackQuery):
    await edit_msg(callback.message, "⚠️ <b>СБРОСИТЬ ПРОГРЕСС?</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА", callback_data="restart_game_yes")],
        [InlineKeyboardButton(text="❌ НЕТ", callback_data="continue_game")],
    ]))

@dp.callback_query(F.data == "restart_game_yes")
async def restart_yes(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await start_new_game_btn(callback, state)

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(callback.from_user.id)), HOUSES[0])
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(callback.from_user.id)["level"]), SHOP_LEVELS[0])
    await edit_msg(callback.message, f"📊 <b>СТАТИСТИКА</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n🏠 {house['name']}\n🏪 {shop['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    await edit_msg(callback.message, f"📊 <b>РЫНОК</b>\n\n{fmt_demand(get_player(callback.from_user.id))}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu_callback(callback: CallbackQuery):
    u = get_rep(callback.from_user.id)
    await edit_msg(callback.message, f"🏅 <b>РЕПУТАЦИЯ: {rep_level(u['score'])}</b>\n📊 {u['score']}/100\n📦 Продаж: {u['total_sales']}\n💰 Прибыль: {u['total_profit']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu_callback(callback: CallbackQuery):
    await edit_msg(callback.message, f"🔗 <b>РЕФЕРАЛЫ</b>\n\n<code>{ref_link(callback.from_user.id)}</code>\n\n💰 +500₽ за друга", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    if not p["inventory"]: return await edit_msg(callback.message, "📦 <b>ПУСТО</b>\n\nКупи товары у поставщиков!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="action_buy")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
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
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    if user_id in published_items: published_items[user_id] = None
    sold_items[user_id].clear()
    await edit_msg(callback.message, f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽\n🏠 +{bonus}₽{f' | 🏪 +{shop_income}₽' if shop_income > 0 else ''}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, user_id))

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    p = get_player(callback.from_user.id); await state.clear()
    r = "🏆 <b>ПОБЕДА!</b>" if p["balance"] >= 50000 else "💀 <b>БАНКРОТ!</b>" if p["balance"] <= 0 else "🎮 Игра окончена."
    await edit_msg(callback.message, f"{r}\n💰 {p['balance']}₽\n📦 Продаж: {p['items_sold']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    skin = next((s for s in SKINS if s["id"] == get_player_skin(user_id)), SKINS[0])
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n👤 {skin['emoji']} {skin['name']}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(1, user_id))

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    skin = next((s for s in SKINS if s["id"] == get_player_skin(callback.from_user.id)), SKINS[0])
    await edit_msg(callback.message, f"🎮 <b>RESELL TYCOON</b>\n👤 {skin['emoji']} {skin['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")]]))

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    l = get_learning(callback.from_user.id)
    kb = [[InlineKeyboardButton(text=f"{'✅' if lesson['id'] in l['completed'] else '📖'} {lesson['title']}", callback_data=f"lesson_{lesson['id']}")] for lesson in LESSONS]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="back_to_start")])
    await edit_msg(callback.message, "📚 <b>ОБУЧЕНИЕ</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

def complete_lesson(user_id, lesson_id):
    if lesson_id not in get_learning(user_id)["completed"]:
        get_learning(user_id)["completed"].append(lesson_id)
        save_json(LEARNING_FILE, learning_data)
        if user_id in players: players[user_id]["balance"] += next((l["reward"] for l in LESSONS if l["id"] == lesson_id), 0)
        return True
    return False

@dp.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    lesson = next((l for l in LESSONS if l["id"] == int(callback.data.split("_")[1])), None)
    if not lesson: return await callback.answer("Не найден")
    done = lesson["id"] in get_learning(callback.from_user.id)["completed"]
    kb = []
    if not done: kb.append([InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ (+₽)", callback_data=f"complete_lesson_{lesson['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 К УРОКАМ", callback_data="action_learn")])
    await edit_msg(callback.message, lesson["text"] + (f"\n\n💰 +{lesson['reward']}₽" if not done else "\n✅ Пройден!"), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("complete_lesson_"))
async def complete_lesson_btn(callback: CallbackQuery):
    if complete_lesson(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("Урок пройден!"); await learn_btn(callback)
    else: await callback.answer("Уже пройден")

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())