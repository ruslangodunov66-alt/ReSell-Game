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

# ==================== АУКЦИОН ====================
# Структура: {"items": [{"seller_id": int, "item": dict, "start_price": int, "current_bid": int, "bidder_id": int, "end_time": float, "active": bool}]}
auction_data = {"items": []}

# ==================== ТАБЛИЦА ЛИДЕРОВ ====================
# Структура: {user_id: {"total_profit": int, "total_sales": int, "week": str}}
leaderboard_data = {}

def load_all():
    global referral_data, rep_data, learning_data, player_houses, player_avatars, player_shops, auction_data, leaderboard_data
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})
    player_houses = load_json(HOUSES_FILE, {})
    player_avatars = load_json(AVATARS_FILE, {})
    player_shops = load_json(SHOPS_FILE, {})
    auction_data = load_json(AUCTION_FILE, {"items": []})
    leaderboard_data = load_json(LEADERBOARD_FILE, {})

def update_leaderboard(user_id, profit, sales):
    uid = str(user_id)
    current_week = datetime.now().strftime("%Y-W%W")
    
    if uid not in leaderboard_data or leaderboard_data[uid].get("week") != current_week:
        leaderboard_data[uid] = {"total_profit": 0, "total_sales": 0, "week": current_week}
    
    leaderboard_data[uid]["total_profit"] += profit
    leaderboard_data[uid]["total_sales"] += sales
    save_json(LEADERBOARD_FILE, leaderboard_data)

def get_top_players(limit=10):
    """Возвращает топ игроков за неделю."""
    top = []
    for uid, data in leaderboard_data.items():
        top.append((int(uid), data["total_profit"], data["total_sales"]))
    top.sort(key=lambda x: x[1], reverse=True)
    return top[:limit]

# ==================== МАГАЗИН ====================
SHOP_LEVELS = [
    {"id": "none", "name": "❌ Нет магазина", "price": 0, "income_per_hour": 0, "description": "У тебя нет своего магазина.", "emoji": "❌"},
    {"id": "stall", "name": "🛍 Лавка на рынке", "price": 5000, "income_per_hour": 100, "description": "Маленькая точка на вещевом рынке. +100₽ в час.", "emoji": "🛍"},
    {"id": "container", "name": "📦 Контейнер на Садоводе", "price": 15000, "income_per_hour": 300, "description": "Контейнер на оптовом рынке. +300₽ в час.", "emoji": "📦"},
    {"id": "store", "name": "🏬 Магазин в ТЦ", "price": 50000, "income_per_hour": 800, "description": "Полноценный магазин в торговом центре. +800₽ в час.", "emoji": "🏬"},
    {"id": "boutique", "name": "👑 Бутик в центре", "price": 150000, "income_per_hour": 2000, "description": "Элитный бутик в центре города. +2000₽ в час.", "emoji": "👑"},
]

player_shops = {}

def get_player_shop(user_id):
    uid = str(user_id)
    if uid not in player_shops:
        player_shops[uid] = {"level": "none", "items": 0, "last_collect": time_module.time()}
        save_json(SHOPS_FILE, player_shops)
    return player_shops[uid]

def buy_shop(user_id, shop_id):
    uid = str(user_id)
    shop = next((s for s in SHOP_LEVELS if s["id"] == shop_id), None)
    if not shop: return False, "Магазин не найден"
    current = get_player_shop(user_id)
    if current["level"] == shop_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < shop["price"]: return False, f"Недостаточно денег! Нужно {shop['price']}₽"
    p["balance"] -= shop["price"]
    current["level"] = shop_id
    current["last_collect"] = time_module.time()
    save_json(SHOPS_FILE, player_shops)
    return True, f"✅ Куплен {shop['name']}!"

def collect_shop_income(user_id):
    shop_data = get_player_shop(user_id)
    shop = next((s for s in SHOP_LEVELS if s["id"] == shop_data["level"]), SHOP_LEVELS[0])
    if shop["id"] == "none": return 0
    elapsed = time_module.time() - shop_data["last_collect"]
    hours = elapsed / 3600
    income = int(shop["income_per_hour"] * hours)
    if income > 0:
        shop_data["last_collect"] = time_module.time()
        save_json(SHOPS_FILE, player_shops)
        if user_id in players: players[user_id]["balance"] += income; players[user_id]["stat_earned_today"] += income
    return income

# ==================== НЕДВИЖИМОСТЬ ====================
HOUSES = [
    {"id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0, "description": "Бесплатное жильё.", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
    {"id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150, "description": "Уютная квартира. +150₽/день.", "image_url": "AgACAgIAAxkBAAIBeGn3hGvVcFktYFQJP-YNnKti48v1AAKYGWsbUNy4SzN3yqU-dPZwAQADAgADeQADOwQ"},
    {"id": "house", "name": "🏠 Одноэтажный дом", "price": 35000, "income_bonus": 400, "description": "Дом с гаражом. +400₽/день.", "image_url": "AgACAgIAAxkBAAIBemn3hKeq-IxdQ6l6jB7sD10pQPbHAAKUGGsbaAW5S4jG5ecluTqMAQADAgADeQADOwQ"},
    {"id": "villa", "name": "🏰 Богатая вилла", "price": 100000, "income_bonus": 1200, "description": "Вилла с бассейном. +1200₽/день.", "image_url": "AgACAgIAAxkBAAIBfGn3hME0a5rsH1wos1Qyy1AhsYAnAAKVGGsbaAW5SzyFR-E8--65AQADAgADeQADOwQ"},
    {"id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000, "description": "Яхта у причала. +3000₽/день.", "image_url": "AgACAgIAAxkBAAIBfmn3hNlqZXeSCAxLTetoN0kJMG4RAAKWGGsbaAW5SxNdXNthpgjFAQADAgADeQADOwQ"},
]

# ==================== АВАТАРЫ ====================
AVATAR_PARTS = {
    "face": {"name": "😶 Лицо", "options": {"default": "Обычное", "smile": "Улыбка", "cool": "Крутое", "angry": "Злое", "surprised": "Удивлённое"}},
    "hair": {"name": "💇 Причёска", "options": {"none": "Лысый", "short": "Короткие", "long": "Длинные", "mohawk": "Ирокез", "cap": "Кепка"}},
    "clothes": {"name": "👕 Одежда", "options": {"tshirt": "Футболка", "hoodie": "Худи", "suit": "Костюм", "jacket": "Куртка", "rich": "Премиум"}},
    "accessory": {"name": "🕶 Аксессуары", "options": {"none": "Ничего", "glasses": "Очки", "sunglasses": "Тёмные очки", "chain": "Цепь", "headphones": "Наушники"}},
    "background": {"name": "🎨 Фон", "options": {"white": "Белый", "gray": "Серый", "blue": "Синий", "green": "Зелёный", "purple": "Фиолетовый"}},
}

DEFAULT_AVATAR = {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}

def get_avatar_url(avatar_config):
    seed = hashlib.md5(str(avatar_config).encode()).hexdigest()[:10]
    return f"https://api.dicebear.com/7.x/pixel-art/svg?seed={seed}"

# ==================== ОСТАЛЬНЫЕ ДАННЫЕ ====================
LESSONS = [
    {"id": 1, "title": "🚀 Основы товарного бизнеса", "text": "📚 <b>ОСНОВЫ ТОВАРКИ</b>\n\n<b>Где брать товар:</b>\n• Авито\n• Оптовые рынки (Садовод)\n• Китай (Taobao, 1688)\n• Секонд-хенды\n\n💰 Старт: от 1000₽", "reward": 500},
    {"id": 2, "title": "📊 Анализ рынка", "text": "📚 <b>АНАЛИЗ РЫНКА</b>\n\n<b>Сезонность:</b>\n• Осень — куртки\n• Зима — пуховики\n• Весна — демисезон\n• Лето — футболки", "reward": 500},
]

SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭", "desc": "Крупный оптовик. Надёжно, дорого."},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕", "desc": "Сток. Баланс цены и риска."},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒", "desc": "Перекуп. Средне."},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸", "desc": "Дёшево, рискованно."},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲", "desc": "Почти наверняка кинет."},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑", "desc": "VIP. Лучшие цены."}

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
    {"text": "📰 Авито комиссия 15%", "cat": None, "mult": 0.8},
    {"text": "📰 Аксессуары в тренде!", "cat": "🎒 Аксессуары", "mult": 1.6},
]

CLIENT_TYPES = {
    "angry": {"system_prompt": "Ты покупатель. Недоверчивый. Торгуешься. 1-3 предложения.", "discount_range": (0.6, 0.8), "patience": 4, "remind_time": (120, 300)},
    "kind": {"system_prompt": "Ты покупатель. Вежливый. Просишь скидку. 1-3 предложения.", "discount_range": (0.85, 0.95), "patience": 6, "remind_time": (180, 420)},
    "sly": {"system_prompt": "Ты перекупщик. Хитрый. 1-3 предложения.", "discount_range": (0.7, 0.85), "patience": 5, "remind_time": (150, 360)}
}

JOBS = [
    {"id": "flyers", "name": "📦 Расклейка", "duration": 60, "reward": 200, "emoji": "📦", "steps": ["📦 Взял...", "🏃 Бежишь...", "📌 Клеишь...", "✅ Готово!"]},
    {"id": "delivery", "name": "🚗 Доставка", "duration": 120, "reward": 500, "emoji": "🚗", "steps": ["🚗 Принял...", "📦 Забираешь...", "🛵 Едешь...", "✅ Доставлено!"]},
    {"id": "freelance", "name": "💻 Фриланс", "duration": 300, "reward": 1200, "emoji": "💻", "steps": ["💻 Редактор...", "🎨 Рисуешь...", "📤 Отправляешь...", "✅ Готово!"]},
]

REPUTATION_LEVELS = {-100: "💀 ЧС", -50: "🔴 Ужасная", -10: "🟠 Плохая", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 75: "🟣 Легенда", 100: "👑 Бог товарки"}
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
remind_timers = {}
active_chat_for_user = {}
side_jobs = {}
player_houses = {}
player_avatars = {}
item_descriptions = {}

# ==================== ЗАГРУЗКА ====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

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

async def send_avatar_photo(user_id, caption="", reply_markup=None):
    avatar = get_player_avatar(user_id); avatar_url = get_avatar_url(avatar)
    try:
        msg = await bot.send_photo(user_id, avatar_url, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
        return msg
    except:
        parts = []
        for key, data in AVATAR_PARTS.items():
            val = avatar.get(key, "default"); name = data["options"].get(val, val)
            parts.append(f"{data['name']}: {name}")
        text_card = f"👤 <b>ТВОЙ ПЕРСОНАЖ</b>\n\n" + "\n".join(parts)
        if caption: text_card = caption
        await del_prev(user_id); await del_user_msgs(user_id)
        msg = await bot.send_message(user_id, text_card, parse_mode="HTML", reply_markup=reply_markup)
        last_bot_message[user_id] = msg.message_id
        return msg

# ==================== РЕФЕРАЛЫ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"
def top_refs(limit=10):
    s = [(uid, len(d["invited"])) for uid, d in referral_data.items()]
    s.sort(key=lambda x: x[1], reverse=True); return s[:limit]
def is_vip(user_id): return str(user_id) in [str(uid) for uid, _ in top_refs(3)]

# ==================== РЕПУТАЦИЯ ====================
def get_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {"score": 0, "total_sales": 0, "total_profit": 0, "max_balance": 0, "scam_survived": 0, "angry_deals": 0, "haggle_wins": 0, "lessons_completed": 0, "achievements": [], "rep_history": []}
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
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    else: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}

def check_ach(user_id, pd=None):
    u = get_rep(user_id)
    if pd: u["total_sales"] = pd.get("items_sold", 0); u["total_profit"] = pd.get("total_earned", 0)
    new_a = []
    for a in ACHIEVEMENTS:
        if a["id"] in u["achievements"]: continue
        if a["id"] == "first_sale" and u["total_sales"] >= 1: new_a.append(a)
        elif a["id"] == "seller_10" and u["total_sales"] >= 10: new_a.append(a)
        elif a["id"] == "profit_5000" and u["total_profit"] >= 5000: new_a.append(a)
    for a in new_a: u["achievements"].append(a["id"]); add_rep(user_id, a["reward"])
    save_json(REPUTATION_FILE, rep_data)
    return new_a

# ==================== ОБУЧЕНИЕ ====================
def get_learning(user_id):
    uid = str(user_id)
    if uid not in learning_data: learning_data[uid] = {"completed": [], "current": 1}; save_json(LEARNING_FILE, learning_data)
    return learning_data[uid]

def complete_lesson(user_id, lesson_id):
    if lesson_id not in get_learning(user_id)["completed"]:
        get_learning(user_id)["completed"].append(lesson_id)
        get_rep(user_id)["lessons_completed"] = len(get_learning(user_id)["completed"])
        save_json(LEARNING_FILE, learning_data)
        if user_id in players: players[user_id]["balance"] += next((l["reward"] for l in LESSONS if l["id"] == lesson_id), 0); add_rep(user_id, 3)
        check_ach(user_id); return True
    return False

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
    if p["balance"] < house["price"]: return False, f"Недостаточно денег! Нужно {house['price']}₽"
    p["balance"] -= house["price"]; player_houses[uid] = house_id
    save_json(HOUSES_FILE, player_houses)
    return True, f"✅ Куплен {house['name']}!"

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

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": r["scam_survived"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
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

def main_kb(user_id=None):
    buyers_count = get_active_buyers_count(user_id) if user_id else 0
    chat_label = f"💬 ЧАТЫ ({buyers_count})" if buyers_count > 0 else "💬 ЧАТЫ"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text=chat_label, callback_data="action_chats"),
         InlineKeyboardButton(text="💼 ЗАРАБОТОК", callback_data="action_job")],
        [InlineKeyboardButton(text="🏠 НЕДВИЖИМОСТЬ", callback_data="action_houses"),
         InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")],
        [InlineKeyboardButton(text="🏪 МАГАЗИН", callback_data="action_shop"),
         InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="action_auction")],
        [InlineKeyboardButton(text="🏆 ТАБЛИЦА ЛИДЕРОВ", callback_data="action_leaderboard")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats"),
         InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
        [InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand"),
         InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])

# ==================== ОЦЕНКА ОПИСАНИЯ ====================
def rate_description(description):
    score = 3
    if len(description) >= 30: score += 1
    if len(description) >= 80: score += 1
    keywords = ["состояние", "размер", "цвет", "бренд", "качество", "материал", "новый", "винтаж", "оригинал"]
    score += min(3, sum(1 for w in keywords if w in description.lower()))
    if sum(1 for c in description if c in "🎯💎🔥⭐✅📦👕👟🛍") >= 2: score += 1
    return min(10, max(1, score))

def get_quality_bonus(quality):
    if quality >= 9: return {"price_mult": 1.5, "buyers_bonus": 3, "name": "🔥 Легендарное"}
    elif quality >= 7: return {"price_mult": 1.3, "buyers_bonus": 2, "name": "⭐ Отличное"}
    elif quality >= 5: return {"price_mult": 1.1, "buyers_bonus": 1, "name": "👍 Хорошее"}
    elif quality >= 3: return {"price_mult": 1.0, "buyers_bonus": 0, "name": "👌 Обычное"}
    else: return {"price_mult": 0.8, "buyers_bonus": -1, "name": "👎 Слабое"}

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
        discount = random.uniform(*client["discount_range"]) + rm["haggle_bonus"]
        discount = max(0.3, min(0.95, discount))
        desc_data = item_descriptions.get(user_id, {}).get(item_name, {})
        quality = desc_data.get("quality", 5)
        discount += (get_quality_bonus(quality)["price_mult"] - 1.0) * 0.3
        discount = max(0.3, min(0.95, discount))
        
        offer = int(price * discount); offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        
        msg = first_msg(client_type, item_name, price, offer)
        active_chats[chat_key] = {"user_id": user_id, "buyer_id": buyer_id, "client_type": client_type, "item": item_name, "price": price, "offer": offer, "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}], "round": 1, "max_rounds": client["patience"], "finished": False, "reminders_sent": 0}
        
        await send_msg(user_id, f"📩 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n💬 {msg}\n\n<i>Напиши ответ или «продано»</i>")
        
        if client["remind_time"]:
            asyncio.create_task(do_remind(user_id, buyer_id, random.randint(*client["remind_time"])))
    else:
        chat = active_chats.get(chat_key)
        if not chat or chat["finished"]: return
        msg = f"Я жду ответ по {item_name}. Вы тут?"
        chat["history"].append({"role": "assistant", "content": msg}); chat["reminders_sent"] += 1
        await send_msg(user_id, f"🔔 <b>Покупатель #{buyer_id}</b>\n💬 {msg}")

async def do_remind(user_id, buyer_id, delay):
    await asyncio.sleep(delay)
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if chat and not chat["finished"] and chat["reminders_sent"] < 2:
        await send_buyer(user_id, buyer_id, chat["client_type"], chat["item"], chat["price"], is_reminder=True)

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
    if user_id not in published_items or not published_items[user_id]: return
    pub = published_items[user_id]; item = pub["item"]
    if item["name"] in sold_items[user_id]: return
    
    n = random.randint(1, 3)
    if rep_mult(get_rep(user_id)["score"])["haggle_bonus"] > 0.1: n = min(3, n + 1)
    desc_data = item_descriptions.get(user_id, {}).get(item["name"], {})
    n += get_quality_bonus(desc_data.get("quality", 5))["buyers_bonus"]
    n = max(1, min(6, n))
    
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    await send_msg(user_id, f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n👥 Пишут: <b>{n}</b> чел.\n\n<i>Напиши «продано» когда готов!</i>")
    
    for i, bt in enumerate(types):
        await asyncio.sleep(random.randint(5, 20))
        await send_buyer(user_id, i + 1, bt, item["name"], item["market_price"])

async def complete_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    p = get_player(user_id); item_name = chat["item"]; final = chat["offer"]
    
    if item_name in sold_items[user_id]:
        if message: await send_msg(user_id, "⚠️ Этот товар уже продан!")
        return None
    
    sold = None
    if user_id in published_items and published_items[user_id]:
        pub_item = published_items[user_id].get("item", {})
        if pub_item.get("name") == item_name:
            sold = pub_item
            published_items[user_id] = None
    
    if not sold:
        for i, inv in enumerate(p["inventory"]):
            if inv["name"] == item_name:
                sold = p["inventory"].pop(i)
                break
    
    if not sold:
        if message: await send_msg(user_id, "❌ Товар не найден.")
        return None
    
    sold_items[user_id].add(item_name)
    
    profit = final - sold["buy_price"]
    p["balance"] += final; p["total_earned"] += profit; p["items_sold"] += 1
    p["stat_earned_today"] += profit; p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + 5)
    add_rep(user_id, random.randint(2, 5))
    if chat["client_type"] == "angry": get_rep(user_id)["angry_deals"] += 1
    
    # Обновляем таблицу лидеров
    update_leaderboard(user_id, profit, 1)
    
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
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
    
    p = players.get(user_id)
    await del_user_msgs(user_id)
    
    if p and p.get("day", 0) > 0:
        await send_msg(user_id, f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n📅 День {p['day']} | 💰 {p['balance']}₽\n⭐ {rep_level(get_rep(user_id)['score'])}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="🏆 ЛИДЕРЫ", callback_data="action_leaderboard")],
            [InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="action_auction")],
        ]))
    else:
        await send_msg(user_id, "🎮 <b>RESELL TYCOON</b>\n\nТренажёр товарного бизнеса!\nАукцион • Лидеры • Магазин\n\n👇 Жми начать!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")],
            [InlineKeyboardButton(text="🔨 АУКЦИОН", callback_data="action_auction")],
        ]))

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": r["scam_survived"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}\n\n👇 1. 🏭 Закупись → 2. 📦 Опубликуй → 3. 💬 Продай!", reply_markup=main_kb(user_id))

@dp.message(Command('check'))
async def check_job_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in side_jobs or side_jobs[user_id].get("done", True):
        return await send_msg(user_id, "💼 Нет активной работы.")
    job_data = side_jobs[user_id]; job = JOBS[job_data["job_type"]]
    elapsed = int(time_module.time() - job_data["start_time"])
    if elapsed >= job["duration"] and not job_data["done"]:
        job_data["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]
        await send_msg(user_id, f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n💰 +{job['reward']}₽")
    else:
        await send_msg(user_id, f"⏳ Осталось: {job['duration'] - elapsed} сек.")

# ==================== АУКЦИОН ====================
@dp.callback_query(F.data == "action_auction", StateFilter(GameState.playing))
async def show_auction(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_items = [item for item in auction_data.get("items", []) if item.get("active", True)]
    
    txt = "🔨 <b>АУКЦИОН</b>\n\n"
    
    if not active_items:
        txt += "Нет активных лотов.\n\n<i>Ты можешь выставить свой товар на аукцион!</i>"
        kb = [
            [InlineKeyboardButton(text="📤 ВЫСТАВИТЬ ЛОТ", callback_data="auction_sell")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ]
        return await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    kb = []
    for i, item in enumerate(active_items):
        seller_name = f"ID:{item['seller_id']}"
        try:
            seller = await bot.get_chat(item['seller_id'])
            seller_name = seller.first_name or seller_name
        except: pass
        
        current_bid = item.get("current_bid", item["start_price"])
        bidder = "Нет ставок"
        if item.get("bidder_id"):
            try:
                bidder_info = await bot.get_chat(item['bidder_id'])
                bidder = bidder_info.first_name or f"ID:{item['bidder_id']}"
            except: pass
        
        time_left = max(0, int(item.get("end_time", 0) - time_module.time()))
        hours, mins = divmod(time_left, 3600)
        hours = int(hours); mins = int(mins)
        
        txt += f"📦 <b>Лот #{i+1}:</b> {item['item']['name']}\n"
        txt += f"💰 Старт: {item['start_price']}₽ | Текущая: {current_bid}₽\n"
        txt += f"👤 Продавец: {seller_name}\n"
        txt += f"🙋 Лидер: {bidder}\n"
        txt += f"⏳ До конца: {hours}ч {mins}м\n\n"
        
        if item["seller_id"] != user_id:
            kb.append([InlineKeyboardButton(
                text=f"💰 СТАВКА на лот #{i+1} (мин. {int(current_bid * 1.1)}₽)",
                callback_data=f"auction_bid_{i}"
            )])
    
    kb.append([InlineKeyboardButton(text="📤 ВЫСТАВИТЬ СВОЙ ЛОТ", callback_data="auction_sell")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "auction_sell", StateFilter(GameState.playing))
async def auction_sell_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    
    if not p["inventory"]:
        return await callback.answer("У тебя нет товаров для продажи!")
    
    kb = []
    for i, item in enumerate(p["inventory"]):
        kb.append([InlineKeyboardButton(
            text=f"{item['name']} (рынок: ~{item['market_price']}₽)",
            callback_data=f"auction_put_{i}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_auction")])
    
    await edit_msg(callback.message, "📤 <b>ВЫСТАВИТЬ НА АУКЦИОН</b>\n\nВыбери товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("auction_put_"), StateFilter(GameState.playing))
async def auction_put_price(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[2])
    p = get_player(user_id)
    
    if item_idx >= len(p["inventory"]):
        return await callback.answer("Товар не найден")
    
    item = p["inventory"][item_idx]
    
    await state.set_state(GameState.auction_price)
    await state.update_data(auction_item_idx=item_idx)
    
    await send_msg(user_id,
        f"💰 <b>СТАРТОВАЯ ЦЕНА</b>\n\n"
        f"📦 {item['name']}\n"
        f"📊 Рыночная: ~{item['market_price']}₽\n\n"
        f"Напиши стартовую цену в чат (только число):")

@dp.message(StateFilter(GameState.auction_price))
async def handle_auction_price(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    if not text.isdigit():
        return await send_msg(user_id, "❌ Введи число!")
    
    price = int(text)
    data = await state.get_data()
    item_idx = data.get("auction_item_idx", 0)
    p = get_player(user_id)
    
    if item_idx >= len(p["inventory"]):
        await state.set_state(GameState.playing)
        return await send_msg(user_id, "❌ Товар не найден.")
    
    if price < 100:
        return await send_msg(user_id, "❌ Минимальная цена — 100₽")
    
    item = p["inventory"].pop(item_idx)
    
    # Добавляем на аукцион
    auction_item = {
        "seller_id": user_id,
        "item": item,
        "start_price": price,
        "current_bid": price,
        "bidder_id": None,
        "end_time": time_module.time() + 3600,  # 1 час
        "active": True
    }
    
    if "items" not in auction_data:
        auction_data["items"] = []
    auction_data["items"].append(auction_item)
    save_json(AUCTION_FILE, auction_data)
    
    await state.set_state(GameState.playing)
    
    await send_msg(user_id,
        f"📤 <b>ЛОТ ВЫСТАВЛЕН!</b>\n\n"
        f"📦 {item['name']}\n"
        f"💰 Стартовая цена: {price}₽\n"
        f"⏳ Аукцион продлится: 1 час\n\n"
        f"<i>Другие игроки могут делать ставки!</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔨 НА АУКЦИОН", callback_data="action_auction")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ]))

@dp.callback_query(F.data.startswith("auction_bid_"), StateFilter(GameState.playing))
async def auction_bid_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[2])
    active_items = [item for item in auction_data.get("items", []) if item.get("active", True)]
    
    if item_idx >= len(active_items):
        return await callback.answer("Лот не найден")
    
    item = active_items[item_idx]
    
    if item["seller_id"] == user_id:
        return await callback.answer("Нельзя делать ставку на свой лот!")
    
    min_bid = int(item.get("current_bid", item["start_price"]) * 1.1)
    p = get_player(user_id)
    
    if p["balance"] < min_bid:
        return await callback.answer(f"Недостаточно денег! Минимальная ставка: {min_bid}₽")
    
    await state.set_state(GameState.playing)
    await state.update_data(auction_bid_idx=item_idx)
    
    await send_msg(user_id,
        f"💰 <b>СТАВКА НА АУКЦИОНЕ</b>\n\n"
        f"📦 {item['item']['name']}\n"
        f"💰 Текущая ставка: {item.get('current_bid', item['start_price'])}₽\n"
        f"📈 Минимальная: {min_bid}₽\n"
        f"💼 Твой баланс: {p['balance']}₽\n\n"
        f"Напиши сумму ставки в чат (только число):")

@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    # Проверка ставки аукциона
    data = await state.get_data()
    if "auction_bid_idx" in data:
        if not text.isdigit():
            await state.update_data(auction_bid_idx=None)
            return await send_msg(user_id, "❌ Введи число!")
        
        bid = int(text)
        item_idx = data["auction_bid_idx"]
        active_items = [item for item in auction_data.get("items", []) if item.get("active", True)]
        
        if item_idx >= len(active_items):
            await state.update_data(auction_bid_idx=None)
            return await send_msg(user_id, "❌ Лот не найден")
        
        item = active_items[item_idx]
        current_bid = item.get("current_bid", item["start_price"])
        min_bid = int(current_bid * 1.1)
        p = get_player(user_id)
        
        if bid < min_bid:
            await state.update_data(auction_bid_idx=None)
            return await send_msg(user_id, f"❌ Минимальная ставка: {min_bid}₽!")
        
        if p["balance"] < bid:
            await state.update_data(auction_bid_idx=None)
            return await send_msg(user_id, "❌ Недостаточно денег!")
        
        # Возвращаем деньги предыдущему лидеру
        if item.get("bidder_id") and item["bidder_id"] != user_id:
            if item["bidder_id"] in players:
                players[item["bidder_id"]]["balance"] += current_bid
        
        # Списываем деньги
        p["balance"] -= bid
        item["current_bid"] = bid
        item["bidder_id"] = user_id
        save_json(AUCTION_FILE, auction_data)
        
        await state.update_data(auction_bid_idx=None)
        
        seller_name = f"ID:{item['seller_id']}"
        try:
            seller = await bot.get_chat(item['seller_id'])
            seller_name = seller.first_name or seller_name
        except: pass
        
        await send_msg(user_id,
            f"✅ <b>СТАВКА ПРИНЯТА!</b>\n\n"
            f"📦 {item['item']['name']}\n"
            f"💰 Твоя ставка: {bid}₽\n"
            f"👤 Продавец: {seller_name}\n\n"
            f"<i>Если никто не перебьёт — товар твой!</i>")
        
        # Уведомляем продавца
        try:
            await bot.send_message(item["seller_id"],
                f"🔔 <b>НОВАЯ СТАВКА!</b>\n\n"
                f"📦 {item['item']['name']}\n"
                f"💰 Ставка: {bid}₽\n"
                f"🙋 Покупатель: {message.from_user.first_name or f'ID:{user_id}'}",
                parse_mode="HTML")
        except: pass
        
        return
    
    # Проверяем слова продажи
    sale_words = ["продано", "продаю", "согласен", "договорились", "по рукам", "забирай", "отдаю", "продам", "бери", "ок", "давай", "хорошо"]
    for w in sale_words:
        if w in text.lower():
            target_chat = None
            if user_id in active_chat_for_user and active_chat_for_user[user_id] in active_chats:
                target_chat = active_chats[active_chat_for_user[user_id]]
            else:
                for key, chat in active_chats.items():
                    if chat["user_id"] == user_id and not chat["finished"]:
                        target_chat = chat; break
            
            if target_chat:
                target_chat["finished"] = True
                if user_id in active_chat_for_user: del active_chat_for_user[user_id]
                await send_msg(user_id, f"👤 <b>Покупатель #{target_chat['buyer_id']}:</b> Отлично! Договорились на {target_chat['offer']}₽!")
                await complete_sale(user_id, target_chat["buyer_id"], message)
                return
    
    # Ищем активный диалог
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
        if user_id in active_chat_for_user: del active_chat_for_user[user_id]
        if random.random() < 0.6:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Ладно, давайте {chat['offer']}₽. Договорились!")
            await complete_sale(user_id, chat["buyer_id"], message)
        else:
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Извините, передумал.\n\n👋 Диалог завершён.")
        return
    
    try:
        system_prompt = CLIENT_TYPES[chat["client_type"]]["system_prompt"] + f"\nТовар: {chat['item']}. Твоя цена: {chat['offer']}₽."
        messages = [{"role": "system", "content": system_prompt}] + chat["history"][-2:]
        resp = client_openai.chat.completions.create(model="deepseek-chat", messages=messages, temperature=0.7, max_tokens=80)
        ai_msg = resp.choices[0].message.content
    except:
        ai_msg = f"Ну так что? {chat['offer']}₽ — берёте?"
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    prices = re.findall(r'(\d{3,5})₽', ai_msg)
    for p in prices:
        new_price = int(p)
        if chat["offer"] < new_price <= chat["price"]: chat["offer"] = new_price
    
    for w in ["беру", "договорились", "по рукам", "забираю", "согласен"]:
        if w in ai_msg.lower() and "?" not in ai_msg.lower():
            chat["finished"] = True
            if user_id in active_chat_for_user: del active_chat_for_user[user_id]
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}")
            await complete_sale(user_id, chat["buyer_id"], message)
            return
    
    remaining = 5 - chat["round"]
    hint = "\n💡 Напиши «согласен» или «продано» чтобы продать!" if remaining <= 2 else ""
    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}\n\n<i>Осталось: {remaining} сообщ.{hint}</i>")

# ==================== ЧАТЫ ====================
@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_list = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    if not active_list:
        return await edit_msg(callback.message, "💬 <b>ЧАТЫ ПУСТЫ</b>\n\nОпубликуй товар в 📦 Инвентаре!")
    txt = f"💬 <b>АКТИВНЫЕ ДИАЛОГИ ({len(active_list)}):</b>\n\n"
    kb = []
    for key, chat in active_list:
        txt += f"👤 Покупатель #{chat['buyer_id']} | {chat['item']}\n💰 Предлагает: {chat['offer']}₽\n\n"
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
    chat = active_chats[chat_key]
    await send_msg(user_id, f"💬 <b>ДИАЛОГ С ПОКУПАТЕЛЕМ #{buyer_id}</b>\n📦 {chat['item']}\n💰 Твоя цена: {chat['price']}₽ | Предлагает: {chat['offer']}₽\n\n<i>Напиши «продано» чтобы продать!</i>")
    await callback.answer("Чат открыт!")

# ==================== ТАБЛИЦА ЛИДЕРОВ ====================
@dp.callback_query(F.data == "action_leaderboard", StateFilter(GameState.playing))
async def show_leaderboard(callback: CallbackQuery):
    top = get_top_players(10)
    
    if not top:
        return await edit_msg(callback.message, "🏆 <b>ТАБЛИЦА ЛИДЕРОВ</b>\n\nПока нет данных за эту неделю.\nСовершай продажи и попади в топ!")
    
    txt = f"🏆 <b>ТОП-10 ПРОДАВЦОВ НЕДЕЛИ</b>\n\n"
    medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
    
    for i, (uid, profit, sales) in enumerate(top):
        try:
            user = await bot.get_chat(uid)
            name = user.first_name or f"ID:{uid}"
        except:
            name = f"ID:{uid}"
        txt += f"{medals[i]} {name} — {profit}₽ ({sales} продаж)\n"
    
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

# ==================== МАГАЗИН ====================
@dp.callback_query(F.data == "action_shop", StateFilter(GameState.playing))
async def show_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(user_id)["level"]), SHOP_LEVELS[0])
    elapsed = time_module.time() - get_player_shop(user_id)["last_collect"]
    income = int(current_shop["income_per_hour"] * (elapsed / 3600))
    
    txt = f"🏪 <b>МАГАЗИН</b>\n\nТвой: {current_shop['name']}\n💰 Накоплено: {income}₽"
    kb = []
    if income > 0: kb.append([InlineKeyboardButton(text=f"💰 СОБРАТЬ +{income}₽", callback_data="collect_shop_income")])
    kb.append([InlineKeyboardButton(text="🛒 УЛУЧШИТЬ", callback_data="upgrade_shop")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "collect_shop_income", StateFilter(GameState.playing))
async def collect_shop_income_btn(callback: CallbackQuery):
    income = collect_shop_income(callback.from_user.id)
    await callback.answer(f"✅ Собрано {income}₽!" if income > 0 else "Пока нечего")
    await show_shop(callback)

@dp.callback_query(F.data == "upgrade_shop", StateFilter(GameState.playing))
async def upgrade_shop_menu(callback: CallbackQuery):
    current = get_player_shop(callback.from_user.id)
    kb = []
    for shop in SHOP_LEVELS:
        if current["level"] == shop["id"]: continue
        kb.append([InlineKeyboardButton(text=f"{shop['emoji']} {shop['name']} — {shop['price']}₽", callback_data=f"buy_shop_{shop['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_shop")])
    await edit_msg(callback.message, "🛒 <b>ВЫБЕРИ МАГАЗИН:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buy_shop_"), StateFilter(GameState.playing))
async def buy_shop_btn(callback: CallbackQuery):
    success, msg = buy_shop(callback.from_user.id, callback.data.replace("buy_shop_", ""))
    if success: await callback.answer(msg); await show_shop(callback)
    else: await callback.answer(msg, show_alert=True)

# ==================== НЕДВИЖИМОСТЬ ====================
@dp.callback_query(F.data == "action_houses", StateFilter(GameState.playing))
async def show_houses_catalog(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id; current_id = get_player_house(user_id); p = get_player(user_id)
    if page < 0: page = 0
    if page >= len(HOUSES): page = len(HOUSES) - 1
    house = HOUSES[page]; owned = current_id == house["id"]
    
    if owned: status_text = "✅ ТВОЁ"; action_btn = None
    else:
        if p["balance"] >= house["price"]: status_text = f"💰 {house['price']}₽ (хватает!)"; action_btn = InlineKeyboardButton(text=f"🛒 КУПИТЬ", callback_data=f"buy_house_{house['id']}")
        else: status_text = f"💰 {house['price']}₽ (не хватает {house['price'] - p['balance']}₽)"; action_btn = None
    
    txt = f"🏠 <b>НЕДВИЖИМОСТЬ</b> {page+1}/{len(HOUSES)}\n\n{house['name']}\n{house['description']}\n{status_text}"
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"house_page_{page-1}"))
    if page < len(HOUSES)-1: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"house_page_{page+1}"))
    
    kb = []
    if nav: kb.append(nav)
    if action_btn: kb.append([action_btn])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    try:
        if house["image_url"].startswith("AgAC"):
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        else:
            msg = await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await del_prev(user_id); last_bot_message[user_id] = msg.message_id
        try: await callback.message.delete()
        except: pass
    except:
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("house_page_"), StateFilter(GameState.playing))
async def house_page_btn(callback: CallbackQuery):
    await show_houses_catalog(callback, int(callback.data.split("_")[2]))

@dp.callback_query(F.data.startswith("buy_house_"), StateFilter(GameState.playing))
async def buy_house_btn(callback: CallbackQuery):
    success, msg = buy_house(callback.from_user.id, callback.data.replace("buy_house_", ""))
    if success: await callback.answer(msg); await show_houses_catalog(callback, next(i for i, h in enumerate(HOUSES) if h["id"] == callback.data.replace("buy_house_", "")))
    else: await callback.answer(msg, show_alert=True)

# ==================== АВАТАР ====================
@dp.callback_query(F.data == "action_avatar")
async def show_avatar_menu_start(callback: CallbackQuery):
    user_id = callback.from_user.id; avatar = get_player_avatar(user_id)
    kb = []
    for part_key, part_data in AVATAR_PARTS.items():
        current_value = avatar.get(part_key, "default")
        kb.append([InlineKeyboardButton(text=f"{part_data['name']}: {part_data['options'].get(current_value, current_value)}", callback_data=f"avatar_part_{part_key}")])
    p = players.get(user_id)
    if p and p.get("day", 0) > 0: kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    else: kb.append([InlineKeyboardButton(text="🏠 НА ГЛАВНУЮ", callback_data="back_to_start")])
    await send_avatar_photo(user_id, f"👤 <b>ТВОЙ ПЕРСОНАЖ</b>\n\nВыбери что изменить:", InlineKeyboardMarkup(inline_keyboard=kb))
    try: await callback.message.delete()
    except: pass
    await callback.answer()

@dp.callback_query(F.data.startswith("avatar_part_"))
async def show_avatar_options(callback: CallbackQuery):
    part_key = callback.data.replace("avatar_part_", "")
    part_data = AVATAR_PARTS.get(part_key)
    if not part_data: return await callback.answer("Ошибка!")
    avatar = get_player_avatar(callback.from_user.id)
    kb = []
    for opt_key, opt_name in part_data["options"].items():
        selected = "✅ " if avatar.get(part_key) == opt_key else ""
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
            await callback.answer("✅ Обновлено!")
            await show_avatar_options(callback)
        else: await callback.answer("❌ Ошибка")
    else: await callback.answer("❌ Ошибка")

# ==================== ПУБЛИКАЦИЯ ====================
@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    item = p["inventory"][item_idx]
    if user_id in published_items and published_items[user_id] and published_items[user_id].get("item", {}).get("name") == item["name"]:
        return await callback.answer("Уже опубликован!")
    
    await state.set_state(GameState.writing_description)
    await state.update_data(publish_item_idx=item_idx)
    await send_msg(user_id, f"✍️ <b>ОПИШИ ТОВАР</b>\n\n📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n\nНапиши описание в чат.\nЧем подробнее — тем больше покупателей!")

@dp.message(StateFilter(GameState.writing_description))
async def handle_description(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; description = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    data = await state.get_data(); item_idx = data.get("publish_item_idx", 0)
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]):
        await state.set_state(GameState.playing)
        return await send_msg(user_id, "❌ Товар не найден.")
    
    item = p["inventory"][item_idx]
    quality = rate_description(description)
    bonus = get_quality_bonus(quality)
    
    if user_id not in item_descriptions: item_descriptions[user_id] = {}
    item_descriptions[user_id][item["name"]] = {"description": description, "quality": quality}
    
    published_items[user_id] = {"item": item.copy()}
    await state.set_state(GameState.playing)
    
    await send_msg(user_id,
        f"📢 <b>ОПУБЛИКОВАНО!</b>\n\n"
        f"📦 {item['name']}\n💰 {item['market_price']}₽\n"
        f"📝 Качество: {bonus['name']} ({quality}/10)\n"
        f"👥 Бонус: {'+' if bonus['buyers_bonus']>=0 else ''}{bonus['buyers_bonus']} покупателя\n\n"
        f"⏳ Жди 1-3 минуты!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ЧАТЫ", callback_data="action_chats")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")],
        ]))
    
    asyncio.create_task(spawn_buyers(user_id))
    try: await message.delete()
    except: pass

# ==================== ПОДРАБОТКИ ====================
async def job_animation(user_id, job_idx):
    job = JOBS[job_idx]; interval = job["duration"] / len(job["steps"])
    for i, step in enumerate(job["steps"]):
        await asyncio.sleep(interval)
        if user_id not in side_jobs or side_jobs[user_id].get("done", True): return
        if i < len(job["steps"]) - 1:
            try: await send_msg(user_id, f"💼 {job['emoji']} {job['name']}\n{step}")
            except: pass
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        side_jobs[user_id]["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]
        await send_msg(user_id, f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n💰 +{job['reward']}₽")

@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    kb = []
    for j, job in enumerate(JOBS):
        kb.append([InlineKeyboardButton(text=f"{job['emoji']} {job['name']} — {job['reward']}₽", callback_data=f"start_job_{j}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "💼 <b>ПОДРАБОТКИ</b>\n\nВыбери:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("start_job_"))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id; job_idx = int(callback.data.split("_")[2])
    job = JOBS[job_idx]
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        remaining = job["duration"] - int(time_module.time() - side_jobs[user_id]["start_time"])
        if remaining > 0: return await callback.answer(f"Уже работаешь! {remaining} сек.")
    side_jobs[user_id] = {"job_type": job_idx, "start_time": time_module.time(), "done": False}
    await send_msg(user_id, f"💼 <b>ПРИСТУПИЛ!</b>\n{job['emoji']} {job['name']}\n💰 {job['reward']}₽\n\n<i>/check — проверить</i>")
    asyncio.create_task(job_animation(user_id, job_idx))
    await callback.answer("Приступил!")

# ==================== ОСТАЛЬНЫЕ CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu_callback(callback: CallbackQuery):
    u = get_rep(callback.from_user.id)
    await edit_msg(callback.message, f"🏆 <b>РЕПУТАЦИЯ: {rep_level(u['score'])}</b>\n📊 {u['score']}/100\n📦 Продаж: {u['total_sales']}\n💰 Прибыль: {u['total_profit']}₽")

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = len(referral_data[str(user_id)]["invited"])
    await edit_msg(callback.message, f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{ref_link(user_id)}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽")

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(callback.from_user.id)), HOUSES[0])
    shop = next((s for s in SHOP_LEVELS if s["id"] == get_player_shop(callback.from_user.id)["level"]), SHOP_LEVELS[0])
    await edit_msg(callback.message, f"📊 <b>СТАТИСТИКА:</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽\n🏠 {house['name']}\n🏪 {shop['name']}")

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    await edit_msg(callback.message, f"📊 <b>РЫНОК</b>\n\n{fmt_demand(get_player(callback.from_user.id))}")

@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; r = get_rep(user_id)
    players[user_id] = {"balance": 5000, "reputation": max(0, r["score"]), "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0, "items_sold": r["total_sales"], "scam_times": r["scam_survived"], "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n💰 5 000₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))
    await callback.answer("🚀")

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; p = players.get(user_id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))
    await callback.answer("🎮")

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    l = get_learning(callback.from_user.id)
    kb = []
    for lesson in LESSONS:
        done = lesson["id"] in l["completed"]
        kb.append([InlineKeyboardButton(text=f"{'✅' if done else '📖'} {lesson['title']}", callback_data=f"lesson_{lesson['id']}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="back_to_start")])
    await edit_msg(callback.message, f"📚 <b>ОБУЧЕНИЕ</b>\nПройдено: {len(l['completed'])}/{len(LESSONS)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id; supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = []
    for s in supps:
        kb.append([InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"sup_{supps.index(s)}")])
    kb.append([InlineKeyboardButton(text="🔙 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, f"🏭 <b>ПОСТАВЩИКИ</b>\n⭐ ↑ = надёжнее | ⚠️ Кид = обман{' 👑 VIP!' if is_vip(user_id) else ''}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sup_"), StateFilter(GameState.playing))
async def show_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]; items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    p = get_player(user_id); kb = []
    for i, it in enumerate(items):
        pr = int(item_price(it["base_price"], sup) * rep_mult(get_rep(user_id)["score"])["supplier_discount"])
        mp = market_price(it["base_price"], p["market_demand"].get(it["cat"], 1.0))
        kb.append([InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {pr}₽ (~{mp}₽)", callback_data=f"bi_{i}")])
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
        p["balance"] -= price; p["total_spent"] += price; p["scam_times"] += 1
        add_rep(user_id, -5)
        await edit_msg(callback.message, f"💀 <b>КИНУЛИ!</b>\n-{price}₽ | 💼 {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
        return
    p["balance"] -= price; p["total_spent"] += price
    mp = market_price(item["base_price"], p["market_demand"].get(item["cat"], 1.0))
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": mp})
    if sup["rating"] >= 8: add_rep(user_id, 1)
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽ | Рынок: ~{mp}₽\n💼 Баланс: {p['balance']}₽\n\n👇 <b>ДАЛЬШЕ:</b>\n📦 ИНВЕНТАРЬ → Опубликовать → Описание → Ждать!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    if not p["inventory"]:
        return await edit_msg(callback.message, "📦 <b>ИНВЕНТАРЬ ПУСТ</b>\n\nКупи товары у поставщиков! 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")], [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        pub = user_id in published_items and published_items[user_id] and published_items[user_id].get("item", {}).get("name") == it["name"]
        kb.append([InlineKeyboardButton(text=f"{it['name']} | {it['buy_price']}₽ → ~{it['market_price']}₽ | {'📢 ОПУБЛИКОВАН' if pub else '📱 ОПУБЛИКОВАТЬ'}", callback_data=f"inv_{i}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "📦 <b>ИНВЕНТАРЬ</b>\n\n" + "\n".join(f"{i+1}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"])) + "\n\n👇 Нажми на товар чтобы опубликовать!", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    bonus = house["income_bonus"]
    shop_income = collect_shop_income(user_id)
    p["balance"] += bonus; p["day"] += 1; p["stat_earned_today"] = bonus + shop_income; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
    if user_id in published_items: published_items[user_id] = None
    sold_items[user_id].clear()
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"]})
    save_json(REPUTATION_FILE, rep_data)
    shop_txt = f"\n🏪 Магазин: +{shop_income}₽" if shop_income > 0 else ""
    await edit_msg(callback.message, f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽\n🏠 {house['name']}: +{bonus}₽{shop_txt}\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    p = get_player(callback.from_user.id); await state.clear()
    r = "🏆 <b>ПОБЕДА!</b>" if p["balance"] >= 50000 else "💀 <b>БАНКРОТ!</b>" if p["balance"] <= 0 else "🎮 Игра окончена."
    await edit_msg(callback.message, f"{r}\n💰 {p['balance']}₽\n/play — ещё раз", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    p = players.get(callback.from_user.id)
    if p and p.get("day", 0) > 0:
        await edit_msg(callback.message, f"👋 <b>МЕНЮ</b>\n📅 День {p['day']} | 💰 {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")]]))
    else:
        await edit_msg(callback.message, "🎮 <b>RESELL TYCOON</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")]]))

@dp.message(F.photo)
async def get_photo_links(message: types.Message):
    photo = message.photo[-1]; file_id = photo.file_id
    file = await bot.get_file(file_id)
    direct_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    await message.answer(f"✅ <b>Ссылки:</b>\n\n<b>ID:</b>\n<code>{file_id}</code>\n\n<b>URL:</b>\n{direct_url}", parse_mode="HTML")

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon + Аукцион + Лидеры запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())