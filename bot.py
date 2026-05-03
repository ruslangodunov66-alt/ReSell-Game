import random
import hashlib
import json
import os
import asyncio
import re
import time as time_module
import io
from collections import defaultdict
from PIL import Image, ImageDraw
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

# ==================== ЦВЕТА АВАТАРОВ ====================
SKIN_COLORS = {"default": "#FFD5B8", "smile": "#FFD5B8", "cool": "#FFD5B8", "angry": "#FFC8A0", "surprised": "#FFD5B8"}
HAIR_COLORS = {"none": None, "short": "#4A3728", "long": "#2C1810", "mohawk": "#FF4444", "cap": "#1A1A2E"}
CLOTHES_COLORS = {"tshirt": "#FFFFFF", "hoodie": "#333333", "suit": "#1A1A2E", "jacket": "#8B4513", "rich": "#FFD700"}
BG_COLORS = {"white": "#FFFFFF", "gray": "#CCCCCC", "blue": "#87CEEB", "green": "#90EE90", "purple": "#DDA0DD"}

AVATAR_PARTS = {
    "face": {"name": "😶 Лицо", "options": {"default": "Обычное", "smile": "Улыбка", "cool": "Крутое", "angry": "Злое", "surprised": "Удивлённое"}},
    "hair": {"name": "💇 Причёска", "options": {"none": "Лысый", "short": "Короткие", "long": "Длинные", "mohawk": "Ирокез", "cap": "Кепка"}},
    "clothes": {"name": "👕 Одежда", "options": {"tshirt": "Футболка", "hoodie": "Худи", "suit": "Костюм", "jacket": "Куртка", "rich": "Премиум"}},
    "accessory": {"name": "🕶 Аксессуары", "options": {"none": "Ничего", "glasses": "Очки", "sunglasses": "Тёмные очки", "chain": "Цепь", "headphones": "Наушники"}},
    "background": {"name": "🎨 Фон", "options": {"white": "Белый", "gray": "Серый", "blue": "Синий", "green": "Зелёный", "purple": "Фиолетовый"}}
}

DEFAULT_AVATAR = {"face": "default", "hair": "short", "clothes": "tshirt", "accessory": "none", "background": "white"}

# ==================== НЕДВИЖИМОСТЬ ====================
HOUSES = [
    {"id": "room", "name": "🏚 Комната в общаге", "price": 0, "income_bonus": 0, "description": "Бесплатное жильё.", "image_url": "https://via.placeholder.com/400x300/E8E8E8/333?text=Комната"},
    {"id": "flat", "name": "🏢 Квартира", "price": 10000, "income_bonus": 150, "description": "Уютная квартира. +150₽/день.", "image_url": "https://via.placeholder.com/400x300/87CEEB/333?text=Квартира"},
    {"id": "house", "name": "🏠 Дом", "price": 35000, "income_bonus": 400, "description": "Просторный дом. +400₽/день.", "image_url": "https://via.placeholder.com/400x300/90EE90/333?text=Дом"},
    {"id": "villa", "name": "🏰 Вилла", "price": 100000, "income_bonus": 1200, "description": "Роскошная вилла. +1200₽/день.", "image_url": "https://via.placeholder.com/400x300/FFD700/333?text=Вилла"},
    {"id": "yacht", "name": "🛥 Яхта", "price": 250000, "income_bonus": 3000, "description": "Собственная яхта. +3000₽/день.", "image_url": "https://via.placeholder.com/400x300/4169E1/FFF?text=Яхта"},
]

# ==================== ДАННЫЕ ====================
LESSONS = [
    {"id": 1, "title": "🚀 Основы товарного бизнеса", "text": "📚 <b>ОСНОВЫ ТОВАРКИ</b>\n\nГде брать товар:\n• Авито\n• Оптовые рынки\n• Китай\n\n💰 Старт: от 1000₽", "reward": 500},
    {"id": 2, "title": "📊 Анализ рынка", "text": "📚 <b>АНАЛИЗ РЫНКА</b>\n\nСезонность:\n• Осень — куртки\n• Зима — пуховики\n• Лето — футболки", "reward": 500},
    {"id": 3, "title": "🏭 Поставщики", "text": "📚 <b>ПОСТАВЩИКИ</b>\n\nКак не попасть на кидалово:\n• Проси отзывы\n• Начни с малого", "reward": 700},
    {"id": 4, "title": "💬 Общение", "text": "📚 <b>ПРОДАЖИ</b>\n\nСтавь цену на 20% выше!", "reward": 700},
    {"id": 5, "title": "📈 Продвижение", "text": "📚 <b>ПРОДВИЖЕНИЕ</b>\n\n5-10 объявлений!", "reward": 1000},
]

SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭", "desc": "Крупный оптовик."},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕", "desc": "Сток."},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒", "desc": "Перекуп."},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸", "desc": "Дёшево."},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲", "desc": "Кинет."},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑", "desc": "VIP."}

BASE_ITEMS = [
    {"cat": "👖 Джинсы", "name": "Levi's 501", "base_price": 2000},
    {"cat": "👕 Худи", "name": "Adidas Hoodie", "base_price": 2500},
    {"cat": "🧥 Куртки", "name": "North Face", "base_price": 5000},
    {"cat": "👟 Кроссы", "name": "Air Max 90", "base_price": 3500},
    {"cat": "🎒 Аксессуары", "name": "Stüssy Bag", "base_price": 1500},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]
MARKET_EVENTS = [
    {"text": "📰 Хайп на джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Куртки в цене!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Кроссовки в тренде!", "cat": "👟 Кроссы", "mult": 1.5},
]

CLIENT_TYPES = {
    "angry": {"system_prompt": "Ты покупатель. Недоверчивый, резкий. 1-3 предложения.", "discount_range": (0.6, 0.8), "patience": 4},
    "kind": {"system_prompt": "Ты покупатель. Вежливый. 1-3 предложения.", "discount_range": (0.85, 0.95), "patience": 6},
    "sly": {"system_prompt": "Ты покупатель. Хитрый. 1-3 предложения.", "discount_range": (0.7, 0.85), "patience": 5}
}

JOBS = [
    {"id": "flyers", "name": "📦 Расклейка", "duration": 60, "reward": 200, "emoji": "📦", "steps": ["📦 Взял...", "🏃 Бегу...", "📌 Клею...", "✅ Готово!"]},
    {"id": "delivery", "name": "🚗 Доставка", "duration": 120, "reward": 500, "emoji": "🚗", "steps": ["🚗 Принял...", "📦 Забираю...", "✅ Доставлено!"]},
    {"id": "freelance", "name": "💻 Фриланс", "duration": 300, "reward": 1200, "emoji": "💻", "steps": ["💻 Работаю...", "✅ Готово!"]},
]

REPUTATION_LEVELS = {-100: "💀 ЧС", 0: "🟡 Нейтральная", 25: "🟢 Хорошая", 50: "🔵 Отличная", 100: "👑 Бог"}

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()

# ==================== ХРАНИЛИЩА ====================
players = {}
referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False})
rep_data = {}
learning_data = {}
active_chats = {}
published_items = {}
last_bot_message = {}
pending_messages = defaultdict(list)
remind_timers = {}
side_jobs = {}
player_houses = {}
player_avatars = {}

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data, learning_data, player_houses, player_avatars
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})
    player_houses = load_json(HOUSES_FILE, {})
    player_avatars = load_json(AVATARS_FILE, {})

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
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")]])
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

async def edit_msg(message, text, parse_mode="HTML", reply_markup=None):
    await del_user_msgs(message.chat.id)
    if reply_markup is None:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")]])
    try: await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except: pass

# ==================== РЕФЕРАЛЫ / РЕПУТАЦИЯ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"
def top_refs(limit=3):
    s = [(uid, len(d["invited"])) for uid, d in referral_data.items()]
    s.sort(key=lambda x: x[1], reverse=True); return s[:limit]
def is_vip(user_id): return str(user_id) in [str(uid) for uid, _ in top_refs(3)]

def get_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {"score": 0, "total_sales": 0, "total_profit": 0}
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t: return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount):
    u = get_rep(user_id)
    u["score"] = max(-100, min(100, u["score"] + amount))
    save_json(REPUTATION_FILE, rep_data)

# ==================== АВАТАР ====================
def draw_pixel_avatar(avatar_config):
    size = 512
    img = Image.new("RGB", (size, size), BG_COLORS.get(avatar_config.get("background", "white"), "#FFFFFF"))
    draw = ImageDraw.Draw(img)
    s = 4
    
    # Одежда
    clothes = avatar_config.get("clothes", "tshirt")
    draw.rectangle([32*s, 80*s, 96*s, 120*s], fill=CLOTHES_COLORS.get(clothes, "#FFFFFF"), outline="#000000", width=3*s)
    
    # Голова
    face = avatar_config.get("face", "default")
    draw.ellipse([40*s, 20*s, 88*s, 80*s], fill=SKIN_COLORS.get(face, "#FFD5B8"), outline="#000000", width=3*s)
    
    # Глаза
    if face == "angry":
        draw.line([(48*s, 45*s), (58*s, 50*s)], fill="#000000", width=3*s)
        draw.line([(70*s, 50*s), (80*s, 45*s)], fill="#000000", width=3*s)
    elif face == "cool":
        draw.rectangle([46*s, 44*s, 58*s, 48*s], fill="#000000")
        draw.rectangle([70*s, 44*s, 82*s, 48*s], fill="#000000")
    else:
        for ex, ey in [(48*s, 44*s), (72*s, 44*s)]:
            draw.ellipse([ex, ey, ex+8*s, ey+10*s], fill="#FFFFFF", outline="#000000", width=2*s)
            draw.ellipse([ex+3*s, ey+3*s, ex+5*s, ey+5*s], fill="#000000")
    
    # Рот
    if face == "smile":
        draw.arc([55*s, 58*s, 73*s, 70*s], start=0, end=180, fill="#000000", width=3*s)
    elif face == "angry":
        draw.arc([55*s, 65*s, 73*s, 78*s], start=180, end=360, fill="#000000", width=3*s)
    elif face == "cool":
        draw.line([56*s, 63*s, 72*s, 63*s], fill="#000000", width=3*s)
    else:
        draw.line([56*s, 65*s, 72*s, 65*s], fill="#000000", width=3*s)
    
    # Волосы
    hair = avatar_config.get("hair", "short")
    hair_color = HAIR_COLORS.get(hair)
    if hair_color:
        if hair == "short":
            draw.arc([36*s, 16*s, 92*s, 50*s], start=180, end=360, fill=hair_color)
            draw.rectangle([36*s, 30*s, 92*s, 42*s], fill=hair_color)
        elif hair == "mohawk":
            draw.rectangle([58*s, 10*s, 70*s, 45*s], fill=hair_color)
        elif hair == "cap":
            draw.arc([36*s, 16*s, 92*s, 50*s], start=180, end=360, fill=hair_color)
            draw.rectangle([36*s, 30*s, 92*s, 38*s], fill=hair_color)
    
    # Аксессуары
    accessory = avatar_config.get("accessory", "none")
    if accessory == "glasses":
        draw.rectangle([44*s, 42*s, 60*s, 50*s], outline="#000000", width=3*s)
        draw.rectangle([68*s, 42*s, 84*s, 50*s], outline="#000000", width=3*s)
        draw.line([60*s, 46*s, 68*s, 46*s], fill="#000000", width=3*s)
    elif accessory == "sunglasses":
        draw.rectangle([42*s, 40*s, 62*s, 52*s], fill="#000000")
        draw.rectangle([66*s, 40*s, 86*s, 52*s], fill="#000000")
    
    img = img.resize((256, 256), Image.NEAREST)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def get_player_avatar(user_id):
    uid = str(user_id)
    if uid not in player_avatars:
        player_avatars[uid] = DEFAULT_AVATAR.copy()
        save_json(AVATARS_FILE, player_avatars)
    return player_avatars[uid]

def update_avatar_part(user_id, part, value):
    uid = str(user_id)
    if uid not in player_avatars:
        player_avatars[uid] = DEFAULT_AVATAR.copy()
    player_avatars[uid][part] = value
    save_json(AVATARS_FILE, player_avatars)

async def send_avatar_photo(user_id, caption="", reply_markup=None):
    avatar = get_player_avatar(user_id)
    photo = draw_pixel_avatar(avatar)
    await del_prev(user_id); await del_user_msgs(user_id)
    msg = await bot.send_photo(user_id, types.BufferedInputFile(photo.read(), filename="avatar.png"), caption=caption, parse_mode="HTML", reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        players[user_id] = {"balance": 5000, "inventory": [], "day": 1, "total_earned": 0, "items_sold": 0, "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    return players[user_id]

def item_price(base, sup): return int(base * sup["price_mult"])
def market_price(base, demand): return int(base * demand * random.uniform(0.9, 1.3))
def daily_event(): return random.choice(MARKET_EVENTS) if random.random() < 0.6 else None

def fmt_demand(p):
    return "\n".join(f"{'🔥' if m>=1.5 else '📈' if m>=1.2 else '➡️' if m>=0.8 else '📉' if m>=0.5 else '💀'} {c}: x{m:.1f}" for c, m in p["market_demand"].items())

def main_kb(user_id=None):
    bc = sum(1 for c in active_chats.values() if c["user_id"] == user_id and not c["finished"]) if user_id else 0
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text=f"💬 ЧАТЫ ({bc})" if bc else "💬 ЧАТЫ", callback_data="action_chats"), InlineKeyboardButton(text="💼 ЗАРАБОТОК", callback_data="action_job")],
        [InlineKeyboardButton(text="🏠 НЕДВИЖИМОСТЬ", callback_data="action_houses"), InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar_play")],
        [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn"), InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats")],
        [InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand"), InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
        [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"), InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])

# ==================== НЕДВИЖИМОСТЬ ====================
def get_player_house(user_id):
    uid = str(user_id)
    if uid not in player_houses:
        player_houses[uid] = "room"
        save_json(HOUSES_FILE, player_houses)
    return player_houses[uid]

def buy_house(user_id, house_id):
    uid = str(user_id)
    house = next((h for h in HOUSES if h["id"] == house_id), None)
    if not house: return False, "Дом не найден"
    if get_player_house(user_id) == house_id: return False, "Уже есть!"
    p = get_player(user_id)
    if p["balance"] < house["price"]: return False, f"Нужно {house['price']}₽"
    p["balance"] -= house["price"]
    player_houses[uid] = house_id
    save_json(HOUSES_FILE, player_houses)
    return True, f"Куплен {house['name']}!"

# ==================== НЕЙРОКЛИЕНТЫ ====================
async def send_buyer(user_id, buyer_id, client_type, item_name, price):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    offer = int(price * random.uniform(*client["discount_range"]))
    offer = (offer // 100) * 100 + 99
    msgs = {"angry": f"Здравствуйте! {item_name}. Расскажите о состоянии?", "kind": f"Добрый день! {item_name} интересует.", "sly": f"Привет! {item_name}. Что по состоянию?"}
    msg = msgs.get(client_type, f"Здравствуйте! {item_name}.")
    active_chats[chat_key] = {"user_id": user_id, "buyer_id": buyer_id, "client_type": client_type, "item": item_name, "price": price, "offer": offer, "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}], "round": 1, "max_rounds": client["patience"], "finished": False}
    await send_msg(user_id, f"📩 <b>НОВОЕ СООБЩЕНИЕ</b>\n👤 Покупатель #{buyer_id}\n📦 {item_name}\n\n💬 {msg}")

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
    if user_id not in published_items or not published_items[user_id]: return
    item = published_items[user_id]["item"]
    n = random.randint(1, 3)
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    await send_msg(user_id, f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n👥 Пишут: {n} чел.")
    for i, bt in enumerate(types):
        await asyncio.sleep(random.randint(5, 20))
        await send_buyer(user_id, i+1, bt, item["name"], item["market_price"])

async def complete_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    p = get_player(user_id)
    for i, inv in enumerate(p["inventory"]):
        if inv["name"] == chat["item"]:
            sold = p["inventory"].pop(i)
            profit = chat["offer"] - sold["buy_price"]
            p["balance"] += chat["offer"]; p["total_earned"] += profit; p["items_sold"] += 1
            add_rep(user_id, random.randint(2, 5))
            chat["finished"] = True
            if message:
                await send_msg(user_id, f"🎉 <b>ПРОДАНО!</b>\n📦 {chat['item']}\n💰 Цена: {chat['offer']}₽\n💵 Прибыль: {profit}₽")
            return profit
    return None

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
                except: pass; break
    
    p = players.get(user_id)
    await del_user_msgs(user_id)
    if p and p.get("day", 0) > 0:
        house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
        await send_msg(user_id, f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n📅 День {p['day']} | 💰 {p['balance']}₽\n🏠 {house['name']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")]
        ]))
    else:
        await send_msg(user_id, "🎮 <b>RESELL TYCOON</b>\n\nТренажёр товарного бизнеса!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")]
        ]))

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    players[user_id] = {"balance": 5000, "inventory": [], "day": 1, "total_earned": 0, "items_sold": 0, "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    await state.set_state(GameState.playing)
    await send_msg(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(players[user_id])}", reply_markup=main_kb(user_id))

# ==================== ЧАТ С ПОКУПАТЕЛЯМИ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id; text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    for key, chat in active_chats.items():
        if chat["user_id"] == user_id and not chat["finished"]:
            chat["history"].append({"role": "user", "content": text}); chat["round"] += 1
            
            for w in ["продано", "продаю", "согласен", "договорились", "по рукам", "забирай", "отдаю", "продам", "бери", "хорошо", "ок", "давай"]:
                if w in text.lower():
                    chat["finished"] = True
                    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Отлично! Договорились на {chat['offer']}₽.")
                    await complete_sale(user_id, chat['buyer_id'], message); return
            
            if chat["round"] >= 5:
                chat["finished"] = True
                if random.random() < 0.6:
                    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Ладно, давайте {chat['offer']}₽.")
                    await complete_sale(user_id, chat['buyer_id'], message)
                else:
                    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> Извините, я передумал.")
                return
            
            try:
                system_prompt = f"{CLIENT_TYPES[chat['client_type']]['system_prompt']}\n\nТовар: {chat['item']}. Твоя цена: {chat['offer']}₽, продавец хочет {chat['price']}₽. Сообщение {chat['round']}/5."
                resp = client_openai.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}] + chat["history"][-3:], temperature=0.7, max_tokens=100)
                ai_msg = resp.choices[0].message.content
            except:
                ai_msg = f"Ну так что? {chat['offer']}₽ — берёте?"
            
            chat["history"].append({"role": "assistant", "content": ai_msg})
            
            for w in ["беру", "договорились", "по рукам"]:
                if w in ai_msg.lower():
                    chat["finished"] = True
                    await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}")
                    await complete_sale(user_id, chat['buyer_id'], message); return
            
            await send_msg(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}\n\n<i>Осталось: {5-chat['round']} сообщений</i>")
            return

# ==================== CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "action_avatar")
async def show_avatar_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    avatar = get_player_avatar(user_id)
    kb = []
    for pk, pd in AVATAR_PARTS.items():
        kb.append([InlineKeyboardButton(text=f"{pd['name']}: {pd['options'][avatar.get(pk, 'default')]}", callback_data=f"ap_{pk}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="back_to_start")])
    await send_avatar_photo(user_id, "👤 <b>ТВОЙ ПЕРСОНАЖ</b>\n\n<i>Выбери что изменить:</i>", InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "action_avatar_play", StateFilter(GameState.playing))
async def show_avatar_play(callback: CallbackQuery):
    user_id = callback.from_user.id
    avatar = get_player_avatar(user_id)
    kb = []
    for pk, pd in AVATAR_PARTS.items():
        kb.append([InlineKeyboardButton(text=f"{pd['name']}: {pd['options'][avatar.get(pk, 'default')]}", callback_data=f"ap_{pk}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await send_avatar_photo(user_id, "👤 <b>ТВОЙ ПЕРСОНАЖ</b>\n\n<i>Выбери что изменить:</i>", InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("ap_"))
async def show_avatar_opts(callback: CallbackQuery):
    user_id = callback.from_user.id; pk = callback.data.replace("ap_", "")
    avatar = get_player_avatar(user_id); pd = AVATAR_PARTS[pk]
    kb = []
    for ok, on in pd["options"].items():
        sel = "✅ " if avatar.get(pk) == ok else ""
        kb.append([InlineKeyboardButton(text=f"{sel}{on}", callback_data=f"sa_{pk}_{ok}")])
    kb.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_avatar")])
    await edit_msg(callback.message, f"👤 <b>{pd['name']}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("sa_"))
async def set_avatar(callback: CallbackQuery):
    parts = callback.data.split("_")
    pk = parts[1]; ok = "_".join(parts[2:])
    update_avatar_part(callback.from_user.id, pk, ok)
    await callback.answer("✅ Обновлено!")
    await show_avatar_opts(callback)

# НЕДВИЖИМОСТЬ
@dp.callback_query(F.data == "action_houses", StateFilter(GameState.playing))
async def show_houses_catalog(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id; current_id = get_player_house(user_id); p = get_player(user_id)
    page = max(0, min(page, len(HOUSES)-1))
    house = HOUSES[page]; owned = current_id == house["id"]
    
    if owned:
        status_text = "✅ <b>ЭТО ТВОЁ ЖИЛЬЁ</b>"; action_btn = None
    else:
        if p["balance"] >= house["price"]:
            status_text = f"💰 <b>{house['price']}₽</b> (хватает!)"; action_btn = InlineKeyboardButton(text="🛒 КУПИТЬ", callback_data=f"buy_house_{house['id']}")
        else:
            status_text = f"💰 <b>{house['price']}₽</b>\n❌ Не хватает: {house['price'] - p['balance']}₽"; action_btn = None
    
    txt = f"🏠 <b>КАТАЛОГ</b> {page+1}/{len(HOUSES)}\n\n{house['name']}\n{house['description']}\n\n{status_text}\n\n💼 Баланс: {p['balance']}₽"
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"house_page_{page-1}"))
    if page < len(HOUSES)-1: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"house_page_{page+1}"))
    kb = [nav] if nav else []
    if action_btn: kb.append([action_btn])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    
    try:
        await bot.send_photo(user_id, house["image_url"], caption=txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await del_prev(user_id)
        await callback.message.delete()
    except:
        await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("house_page_"), StateFilter(GameState.playing))
async def house_page_btn(callback: CallbackQuery):
    await show_houses_catalog(callback, int(callback.data.split("_")[2]))

@dp.callback_query(F.data.startswith("buy_house_"))
async def buy_house_btn(callback: CallbackQuery):
    user_id = callback.from_user.id; house_id = callback.data.replace("buy_house_", "")
    success, msg = buy_house(user_id, house_id)
    if success:
        await callback.answer(msg)
        await show_houses_catalog(callback)
    else:
        await callback.answer(msg, show_alert=True)

# ПОДРАБОТКИ
@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    kb = [[InlineKeyboardButton(text=f"{j['emoji']} {j['name']} — {j['reward']}₽ ({j['duration']}с)", callback_data=f"job_{i}")] for i, j in enumerate(JOBS)]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "💼 <b>ПОДРАБОТКИ</b>\n\nВыбери работу:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("job_"), StateFilter(GameState.playing))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id; ji = int(callback.data.split("_")[1]); job = JOBS[ji]
    side_jobs[user_id] = {"job_type": ji, "start_time": time_module.time(), "done": False}
    await send_msg(user_id, f"💼 <b>ПРИСТУПИЛ!</b>\n{job['emoji']} {job['name']}\n⏱ {job['duration']}с\n💰 {job['reward']}₽\n\n<i>/check через {job['duration']}с</i>")
    asyncio.create_task(job_anim(user_id, ji))
    await callback.answer("Приступил!")

async def job_anim(user_id, ji):
    job = JOBS[ji]; iv = job["duration"] / len(job["steps"])
    for i, s in enumerate(job["steps"]):
        await asyncio.sleep(iv)
        if user_id not in side_jobs or side_jobs[user_id].get("done", True): return
        if i < len(job["steps"])-1:
            try: await send_msg(user_id, f"💼 {job['emoji']} {job['name']}\n\n{s}")
            except: pass
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        side_jobs[user_id]["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]
        await send_msg(user_id, f"✅ <b>ГОТОВО!</b>\n💰 +{job['reward']}₽")

@dp.message(Command('check'))
async def check_cmd(message: types.Message):
    user_id = message.from_user.id; await del_user_msgs(user_id)
    if user_id not in side_jobs or side_jobs[user_id].get("done", True):
        return await send_msg(user_id, "💼 Нет активной работы.")
    jd = side_jobs[user_id]; job = JOBS[jd["job_type"]]
    elapsed = int(time_module.time() - jd["start_time"])
    if elapsed >= job["duration"] and not jd["done"]:
        jd["done"] = True
        if user_id in players: players[user_id]["balance"] += job["reward"]
        await send_msg(user_id, f"✅ <b>ГОТОВО!</b>\n💰 +{job['reward']}₽")
    else:
        await send_msg(user_id, f"⏳ Осталось: {job['duration'] - elapsed}с")

# ОСТАЛЬНЫЕ ОБРАБОТЧИКИ
@dp.callback_query(F.data == "start_new_game")
async def start_new(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    players[user_id] = {"balance": 5000, "inventory": [], "day": 1, "total_earned": 0, "items_sold": 0, "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0}
    await state.set_state(GameState.playing)
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n🌟 День 1 | 💰 5 000₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(players[user_id])}", reply_markup=main_kb(user_id))
    await callback.answer("🚀")

@dp.callback_query(F.data == "continue_game")
async def continue_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; p = players.get(user_id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))
    await callback.answer("🎮")

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id; supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = [[InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"sup_{supps.index(s)}")] for s in supps]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, f"🏭 <b>ПОСТАВЩИКИ:</b>{' 👑 VIP!' if is_vip(user_id) else ''}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sup_"), StateFilter(GameState.playing))
async def show_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id; idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]; items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    p = get_player(user_id)
    kb = [[InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {item_price(it['base_price'], sup)}₽ (~{market_price(it['base_price'], p['market_demand'].get(it['cat'], 1.0))}₽)", callback_data=f"bi_{i}")] for i, it in enumerate(items)]
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data=f"sup_{idx}")])
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await state.update_data(sup_idx=idx, sup_items=items)
    await edit_msg(callback.message, f"{sup['emoji']} <b>{sup['name']}</b>\n⭐ {sup['rating']}/10", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
    price = item_price(item["base_price"], sup)
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    if random.randint(1, 100) <= sup["scam_chance"]:
        p["balance"] -= price
        await edit_msg(callback.message, f"💀 <b>КИНУЛИ!</b>\n-{price}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]]))
        return
    p["balance"] -= price; mp = market_price(item["base_price"], p["market_demand"].get(item["cat"], 1.0))
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": mp})
    await edit_msg(callback.message, f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽ | 📊 ~{mp}₽\n\n👇 Зайди в 📦 ИНВЕНТАРЬ!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    if not p["inventory"]:
        return await edit_msg(callback.message, "📦 <b>ПУСТО</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
        ]))
    kb = [[InlineKeyboardButton(
        text=f"{it['name']} | {it['buy_price']}₽ → ~{it['market_price']}₽ | {'📢 ОПУБЛИКОВАН' if user_id in published_items and published_items[user_id] and published_items[user_id].get('item', {}).get('name') == it['name'] else '📱 ОПУБЛИКОВАТЬ'}",
        callback_data=f"inv_{i}")] for i, it in enumerate(p["inventory"])]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, "📦 <b>ИНВЕНТАРЬ:</b>\n\n" + "\n".join(f"{i+1}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"])), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery):
    user_id = callback.from_user.id; item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    published_items[user_id] = {"item": p["inventory"][item_idx].copy()}
    await edit_msg(callback.message, f"📢 <b>ОПУБЛИКОВАНО!</b>\n📦 {p['inventory'][item_idx]['name']}\n💰 {p['inventory'][item_idx]['market_price']}₽\n\n⏳ Жди 1-3 минуты!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))
    asyncio.create_task(spawn_buyers(user_id))
    await callback.answer("Опубликовано!")

@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_list = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    if not active_list:
        return await edit_msg(callback.message, "💬 Нет активных диалогов.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
        ]))
    txt = f"💬 <b>ЧАТЫ ({len(active_list)}):</b>\n\n"
    for key, chat in active_list:
        txt += f"👤 #{chat['buyer_id']} | {chat['item']}\n💰 {chat['offer']}₽\n\n"
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    await edit_msg(callback.message, f"📊 <b>СТАТИСТИКА:</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    await edit_msg(callback.message, f"📊 <b>РЫНОК — День {p['day']}</b>\n\n{fmt_demand(p)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu(callback: CallbackQuery):
    u = get_rep(callback.from_user.id)
    await edit_msg(callback.message, f"🏆 <b>РЕПУТАЦИЯ: {rep_level(u['score'])}</b>\n📊 {u['score']}/100\n📦 Продаж: {u['total_sales']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    await edit_msg(callback.message, f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{ref_link(user_id)}</code>\n\n👥 Приглашено: {len(referral_data[str(user_id)]['invited'])}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    l = get_learning(callback.from_user.id)
    kb = [[InlineKeyboardButton(text=f"{'✅' if lesson['id'] in l['completed'] else '📖'} {lesson['title']}", callback_data=f"lesson_{lesson['id']}")] for lesson in LESSONS]
    kb.append([InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="action_back")])
    await edit_msg(callback.message, f"📚 <b>ОБУЧЕНИЕ</b>\nПройдено: {len(l['completed'])}/{len(LESSONS)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id; p = get_player(user_id)
    house = next((h for h in HOUSES if h["id"] == get_player_house(user_id)), HOUSES[0])
    p["balance"] += house["income_bonus"]; p["day"] += 1
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    if user_id in published_items: published_items[user_id] = None
    await edit_msg(callback.message, f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽\n🏠 Бонус от {house['name']}: +{house['income_bonus']}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    p = get_player(callback.from_user.id); await state.clear()
    r = "🏆 <b>ПОБЕДА!</b>" if p["balance"] >= 50000 else "💀 <b>БАНКРОТ!</b>" if p["balance"] <= 0 else "🎮 Игра окончена."
    await edit_msg(callback.message, f"{r}\n💰 {p['balance']}₽\n/play — ещё раз", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")]
    ]))

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
    user_id = callback.from_user.id; p = players.get(user_id)
    if p and p.get("day", 0) > 0:
        await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽\n\n📊 <b>СПРОС:</b>\n{fmt_demand(p)}", reply_markup=main_kb(user_id))
    else:
        await edit_msg(callback.message, "🎮 <b>RESELL TYCOON</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="👤 АВАТАР", callback_data="action_avatar")]
        ]))

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())