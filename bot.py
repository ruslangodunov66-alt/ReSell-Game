import random
import hashlib
import json
import os
import asyncio
from collections import defaultdict
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
CHANNEL_NAME = 'ReSell👾'
BOT_USERNAME = 'R-Game'
DEEPSEEK_API_KEY = "sk-9515baacbf9b44bfbf45caadf97e5012"

client_openai = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==================== ФАЙЛЫ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"

# ==================== ПОСТАВЩИКИ ====================
SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0, "emoji": "🏭"},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10, "emoji": "👕"},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25, "emoji": "🎒"},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50, "emoji": "💸"},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75, "emoji": "🎲"},
]
VIP_SUPPLIER = {"name": "👑 PremiumStock", "rating": 10, "price_mult": 1.05, "scam_chance": 0, "emoji": "👑"}

BASE_ITEMS = [
    {"cat": "👖 Джинсы", "name": "Levi's 501 Vintage", "base_price": 2000},
    {"cat": "👖 Джинсы", "name": "Carhartt WIP Denim", "base_price": 3500},
    {"cat": "👕 Худи", "name": "Adidas Originals Hoodie", "base_price": 2500},
    {"cat": "👕 Худи", "name": "Nike ACG Fleece", "base_price": 3000},
    {"cat": "🧥 Куртки", "name": "The North Face Nuptse", "base_price": 5000},
    {"cat": "🧥 Куртки", "name": "Alpha Industries MA-1", "base_price": 4000},
    {"cat": "👟 Кроссы", "name": "Nike Air Max 90", "base_price": 3500},
    {"cat": "👟 Кроссы", "name": "Adidas Samba OG", "base_price": 2800},
    {"cat": "🎒 Аксессуары", "name": "Stüssy Tote Bag", "base_price": 1500},
    {"cat": "🎒 Аксессуары", "name": "New Era 59Fifty Cap", "base_price": 1200},
    {"cat": "👕 Худи", "name": "Supreme Box Logo", "base_price": 1800},
    {"cat": "🧥 Куртки", "name": "Stone Island Soft Shell", "base_price": 6000},
    {"cat": "👟 Кроссы", "name": "New Balance 990v3", "base_price": 4200},
    {"cat": "🎒 Аксессуары", "name": "Patagonia Hip Pack", "base_price": 2000},
    {"cat": "👖 Джинсы", "name": "Wrangler Retro", "base_price": 1800},
    {"cat": "🧥 Куртки", "name": "Patagonia Down Jacket", "base_price": 5500},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

MARKET_EVENTS = [
    {"text": "📰 Хайп на винтажные джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — спрос на куртки вырос!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Все хотят кроссовки!", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито комиссия 15% — все осторожны.", "cat": None, "mult": 0.8},
    {"text": "📰 Ретро-аксессуары в тренде!", "cat": "🎒 Аксессуары", "mult": 1.6},
    {"text": "📰 Холода — куртки в цене.", "cat": "🧥 Куртки", "mult": 1.3},
    {"text": "📰 Скоро школа — худи дорожают.", "cat": "👕 Худи", "mult": 1.35},
    {"text": "📰 Кроссовки — рынок переполнен.", "cat": "👟 Кроссы", "mult": 0.65},
    {"text": "📰 Блогер в Stüssy — аксессуары летят!", "cat": "🎒 Аксессуары", "mult": 1.5},
    {"text": "📰 Блокировки Авито — конкуренция ниже.", "cat": None, "mult": 1.2},
    {"text": "📰 Эконом-режим — ищут дешёвое.", "cat": None, "mult": 0.7},
]

# ==================== НЕЙРОКЛИЕНТЫ (характер скрыт) ====================
CLIENT_TYPES = {
    "angry": {
        "name": "Покупатель",
        "system_prompt": "Ты покупатель на Авито. Ты ОЧЕНЬ НЕДОВОЛЕН ценой, грубишь (без мата), торгуешься жёстко, сбиваешь цену на 30-50%. Можешь написать 'дорого, я такое на помойке нашёл'. Если продавец уступает — берёшь но ворчишь. Если долго не отвечают — пишешь 'Эй, ты где? Я долго ждать не буду!'. НИКОГДА не говори что ты злой. Веди себя естественно. Коротко, 1-2 предложения.",
        "discount_range": (0.5, 0.7), "patience": 3, "remind_time": (120, 300)
    },
    "kind": {
        "name": "Покупатель",
        "system_prompt": "Ты покупатель на Авито. Ты ВЕЖЛИВЫЙ и ДОБРЫЙ. Просишь скидку 10-20%, хвалишь товар: 'хорошая вещь', 'давно искал'. Если долго не отвечают — пишешь 'Извините, я ещё здесь. Жду ваш ответ :)'. НИКОГДА не говори что ты добрый. Веди себя естественно. Коротко, 1-2 предложения.",
        "discount_range": (0.8, 0.9), "patience": 5, "remind_time": (180, 420)
    },
    "sly": {
        "name": "Покупатель",
        "system_prompt": "Ты покупатель на Авито, перекупщик. Ты ХИТРЫЙ, аргументируешь цену рынком, блефуешь: 'на другом аккаунте дешевле', 'таких полно'. Сбиваешь 20-40%. Если долго не отвечают — пишешь 'Слушай, я тут ещё одно предложение нашёл. Давай решать быстрее?'. НИКОГДА не говори что ты хитрый. Веди себя естественно. Коротко, как в чате.",
        "discount_range": (0.6, 0.8), "patience": 4, "remind_time": (150, 360)
    }
}

# ==================== РЕПУТАЦИЯ ====================
REPUTATION_LEVELS = {
    -100: {"name": "💀 Чёрный список"},
    -50: {"name": "🔴 Ужасная"},
    -10: {"name": "🟠 Плохая"},
    0: {"name": "🟡 Нейтральная"},
    25: {"name": "🟢 Хорошая"},
    50: {"name": "🔵 Отличная"},
    75: {"name": "🟣 Легендарная"},
    90: {"name": "🟡 Золотая"},
    100: {"name": "👑 Бог товарки"},
}

ACHIEVEMENTS = [
    {"id": "first_sale", "name": "🎯 Первая продажа", "target": 1, "reward": 5},
    {"id": "seller_10", "name": "📦 Продавец", "target": 10, "reward": 10},
    {"id": "profit_5000", "name": "💰 Навар", "target": 5000, "reward": 5},
    {"id": "angry_win", "name": "😡 Укротитель", "target": 1, "reward": 10},
    {"id": "haggle_master", "name": "🎯 Мастер торга", "target": 1, "reward": 10},
]

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()

# ==================== ХРАНИЛИЩА ====================
players = {}
referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False})
rep_data = {}
active_chats = {}
published_items = {}
last_bot_message = {}
pending_messages = defaultdict(list)
remind_timers = {}

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data
    ref_raw = load_json(REFERRAL_FILE, {})
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, ref_raw)
    rep_data = load_json(REPUTATION_FILE, {})

load_all()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def delete_previous_message(user_id):
    if user_id in last_bot_message:
        try: await bot.delete_message(user_id, last_bot_message[user_id])
        except: pass

async def delete_user_messages(user_id):
    if user_id in pending_messages:
        for msg_id in pending_messages[user_id]:
            try: await bot.delete_message(user_id, msg_id)
            except: pass
        pending_messages[user_id] = []

async def send_message_clean(user_id, text, parse_mode="HTML", reply_markup=None):
    await delete_previous_message(user_id)
    await delete_user_messages(user_id)
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

async def edit_message_clean(message, text, parse_mode="HTML", reply_markup=None):
    await delete_user_messages(message.chat.id)
    try: await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except: pass

# ==================== РЕФЕРАЛЫ ====================
def generate_ref_code(user_id):
    return hashlib.md5(str(user_id).encode()).hexdigest()[:8]

def get_ref_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{generate_ref_code(user_id)}"

def get_top_referrers(limit=10):
    stats = [(uid, len(data["invited"])) for uid, data in referral_data.items()]
    stats.sort(key=lambda x: x[1], reverse=True)
    return stats[:limit]

def is_vip(user_id):
    top = get_top_referrers(3)
    return str(user_id) in [str(uid) for uid, _ in top]

# ==================== РЕПУТАЦИЯ ====================
def get_user_rep(user_id):
    uid = str(user_id)
    if uid not in rep_data:
        rep_data[uid] = {
            "score": 0, "total_sales": 0, "total_profit": 0,
            "max_balance": 0, "scam_survived": 0,
            "angry_deals": 0, "haggle_wins": 0, "achievements": [], "rep_history": []
        }
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def get_rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t: return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount, reason=""):
    user = get_user_rep(user_id)
    user["score"] = max(-100, min(100, user["score"] + amount))
    user["rep_history"].append({"change": amount, "reason": reason, "total": user["score"]})
    if len(user["rep_history"]) > 20: user["rep_history"] = user["rep_history"][-20:]
    save_json(REPUTATION_FILE, rep_data)
    return user["score"]

def get_rep_multiplier(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    elif score >= -10: return {"supplier_discount": 1.1, "scam_reduce": 1.0, "haggle_bonus": -0.05}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_achievements(user_id, player_data=None):
    user = get_user_rep(user_id)
    if player_data:
        user["total_sales"] = player_data.get("items_sold", 0)
        user["total_profit"] = player_data.get("total_earned", 0)
        user["max_balance"] = max(user["max_balance"], player_data.get("balance", 0))
    new_ach = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in user["achievements"]: continue
        earned = False
        if ach["id"] == "first_sale" and user["total_sales"] >= 1: earned = True
        elif ach["id"] == "seller_10" and user["total_sales"] >= 10: earned = True
        elif ach["id"] == "profit_5000" and user["total_profit"] >= 5000: earned = True
        elif ach["id"] == "angry_win" and user["angry_deals"] >= 1: earned = True
        elif ach["id"] == "haggle_master" and user["haggle_wins"] >= 1: earned = True
        if earned:
            user["achievements"].append(ach["id"])
            add_rep(user_id, ach["reward"], f"Достижение: {ach['name']}")
            new_ach.append(ach)
    save_json(REPUTATION_FILE, rep_data)
    return new_ach

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        rep = get_user_rep(user_id)
        rep_mult = get_rep_multiplier(rep["score"])
        players[user_id] = {
            "balance": 5000, "reputation": max(0, rep["score"]),
            "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0,
            "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
            "market_demand": {cat: 1.0 for cat in CATEGORIES},
            "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0,
            "rep_mult": rep_mult,
        }
    return players[user_id]

def get_item_price(base, sup):
    return int(base * sup["price_mult"])

def get_market_price(base, demand):
    return int(base * demand * random.uniform(0.9, 1.3))

def generate_daily_event():
    return random.choice(MARKET_EVENTS) if random.random() < 0.6 else None

def apply_market_event(p, event):
    if event["cat"]:
        p["market_demand"][event["cat"]] = max(0.3, min(3.0, p["market_demand"][event["cat"]] * event["mult"]))
    else:
        for cat in CATEGORIES:
            p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat] * event["mult"]))

def format_demand(p):
    lines = []
    for cat, mult in p["market_demand"].items():
        if mult >= 1.5: emoji = "🔥"
        elif mult >= 1.2: emoji = "📈"
        elif mult >= 0.8: emoji = "➡️"
        elif mult >= 0.5: emoji = "📉"
        else: emoji = "💀"
        lines.append(f"{emoji} {cat}: x{mult:.1f}")
    return "\n".join(lines)

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats"),
         InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep")],
        [InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand"),
         InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])

# ==================== НЕЙРОКЛИЕНТЫ: ПУБЛИКАЦИЯ И ЧАТ ====================
def generate_first_msg(client_type, item_name, price, offer):
    """Первое сообщение от клиента — НЕ показывает характер."""
    msgs = {
        "angry": [
            f"Здравствуйте! Увидел ваше объявление — {item_name} за {price}₽. Честно говоря, цена завышена. Готов предложить {offer}₽.",
            f"Привет! По поводу {item_name}. {price}₽ — это дорого. Давайте {offer}₽?",
        ],
        "kind": [
            f"Добрый день! Заинтересовался вашим {item_name}. Очень хорошая вещь! Но {price}₽ дороговато. Может, {offer}₽?",
            f"Здравствуйте! Давно ищу {item_name}. У меня бюджет {offer}₽. Возможно договоримся?",
        ],
        "sly": [
            f"Привет! Видел твой лот — {item_name}. Мониторил рынок — такие уходят за {offer}₽. Отдашь за эту цену?",
            f"Здорово! По поводу {item_name}. У меня кэш {offer}₽ прямо сейчас. Забираю если согласен.",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

def generate_remind_msg(client_type, item_name, offer):
    """Напоминание — НЕ показывает характер."""
    msgs = {
        "angry": [
            f"Слушайте, я жду ответ по {item_name}. Моё предложение {offer}₽. Давайте решать быстрее!",
            f"Ну что, думаете ещё? {item_name} за {offer}₽ — хорошая цена. Решайтесь!",
            f"Я серьёзно настроен купить {item_name} за {offer}₽. Жду ответ.",
        ],
        "kind": [
            f"Извините за беспокойство! Напомню о себе — {item_name} за {offer}₽? Буду рад договориться :)",
            f"Добрый день ещё раз! Очень заинтересован в {item_name}. {offer}₽ — моё предложение.",
            f"Не хотел надоедать, но {item_name} всё ещё актуален? Моя цена {offer}₽.",
        ],
        "sly": [
            f"Слушай, по {item_name} — нашёл ещё вариант, но твой интереснее. Давай за {offer}₽?",
            f"Рынок меняется. Моё предложение {offer}₽ за {item_name} в силе. Решайся!",
            f"Время — деньги. {item_name} за {offer}₽. Потом может быть поздно!",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer_message(user_id, buyer_id, client_type, item_name, price, is_reminder=False):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    
    if not is_reminder:
        rep_mult = get_rep_multiplier(get_user_rep(user_id)["score"])
        discount = random.uniform(*client["discount_range"]) + rep_mult["haggle_bonus"]
        discount = max(0.3, min(0.95, discount))
        offer = int(price * discount)
        offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        
        first_msg = generate_first_msg(client_type, item_name, price, offer)
        
        active_chats[chat_key] = {
            "user_id": user_id, "buyer_id": buyer_id,
            "client_type": client_type, "item": item_name,
            "price": price, "offer": offer,
            "history": [
                {"role": "system", "content": client["system_prompt"]},
                {"role": "assistant", "content": first_msg}
            ],
            "round": 1, "max_rounds": client["patience"],
            "finished": False, "reminders_sent": 0, "max_reminders": 2
        }
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ОТВЕТИТЬ", callback_data=f"neuro_reply_{user_id}_{buyer_id}"),
             InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"neuro_decline_{user_id}_{buyer_id}")],
        ])
        
        await send_message_clean(
            user_id,
            f"📩 <b>НОВОЕ СООБЩЕНИЕ!</b>\n\n"
            f"👤 <b>Покупатель #{buyer_id}</b>\n"
            f"📦 По поводу: {item_name}\n\n"
            f"💬 <i>«{first_msg}»</i>\n\n"
            f"Нажми <b>«ОТВЕТИТЬ»</b> и напиши свой ответ в чат.\n"
            f"Торгуйся, убеждай — всё как в реальной переписке!",
            reply_markup=kb
        )
        
        if client["remind_time"]:
            reminder_time = random.randint(*client["remind_time"])
            task = asyncio.create_task(send_reminder(user_id, buyer_id, reminder_time))
            remind_timers[chat_key] = task
    
    else:
        chat = active_chats.get(chat_key)
        if not chat or chat["finished"]: return
        
        remind_msg = generate_remind_msg(client_type, item_name, chat["offer"])
        chat["history"].append({"role": "assistant", "content": remind_msg})
        chat["reminders_sent"] += 1
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ОТВЕТИТЬ", callback_data=f"neuro_reply_{user_id}_{buyer_id}"),
             InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"neuro_decline_{user_id}_{buyer_id}")],
        ])
        
        await send_message_clean(
            user_id,
            f"🔔 <b>НАПОМИНАНИЕ!</b>\n\n"
            f"👤 <b>Покупатель #{buyer_id}</b>\n"
            f"📦 {item_name}\n\n"
            f"💬 <i>«{remind_msg}»</i>\n\n"
            f"Нажми <b>«ОТВЕТИТЬ»</b> и продолжи диалог!",
            reply_markup=kb
        )
        
        if chat["reminders_sent"] < chat["max_reminders"]:
            next_time = random.randint(*client["remind_time"])
            task = asyncio.create_task(send_reminder(user_id, buyer_id, next_time))
            remind_timers[chat_key] = task

async def send_reminder(user_id, buyer_id, delay):
    await asyncio.sleep(delay)
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if chat and not chat["finished"] and chat["reminders_sent"] < chat["max_reminders"]:
        await send_buyer_message(user_id, buyer_id, chat["client_type"], chat["item"], chat["price"], is_reminder=True)

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
    
    if user_id not in published_items or not published_items[user_id]:
        return
    
    pub = published_items[user_id]
    item = pub["item"]
    
    rep_mult = get_rep_multiplier(get_user_rep(user_id)["score"])
    base_buyers = random.randint(1, 3)
    if rep_mult["haggle_bonus"] > 0.1:
        base_buyers = min(3, base_buyers + 1)
    
    buyer_types = random.choices(list(CLIENT_TYPES.keys()), k=base_buyers)
    
    await send_message_clean(
        user_id,
        f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n\n"
        f"📦 {item['name']} за {item['market_price']}₽\n"
        f"👥 Пишут <b>{base_buyers}</b> чел.\n\n"
        f"<i>Отвечай им в чат — торгуйся, убеждай, договаривайся!</i>"
    )
    
    pub["buyers_list"] = []
    
    for i, btype in enumerate(buyer_types):
        await asyncio.sleep(random.randint(5, 20))
        buyer_id = i + 1
        pub["buyers_list"].append({"id": buyer_id, "type": btype, "active": True})
        await send_buyer_message(user_id, buyer_id, btype, item["name"], item["market_price"])

async def complete_neuro_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    
    p = get_player(user_id)
    item_name = chat["item"]
    final_price = chat["offer"]
    
    sold = None
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item_name:
        sold = published_items[user_id]["item"]
        published_items[user_id] = None
    for i, inv_item in enumerate(p["inventory"]):
        if inv_item["name"] == item_name:
            sold = p["inventory"].pop(i)
            break
    
    if not sold:
        if message: await send_message_clean(user_id, "❌ Товар не найден.")
        return None
    
    profit = final_price - sold["buy_price"]
    p["balance"] += final_price
    p["total_earned"] += profit
    p["items_sold"] += 1
    p["stat_earned_today"] += profit
    p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + 5)
    
    add_rep(user_id, random.randint(2, 5), f"Продажа: {item_name}")
    if chat["client_type"] == "angry":
        get_user_rep(user_id)["angry_deals"] += 1
    if final_price > sold["market_price"] * 0.9:
        get_user_rep(user_id)["haggle_wins"] += 1
    
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    
    if chat_key in remind_timers:
        remind_timers[chat_key].cancel()
        del remind_timers[chat_key]
    
    chat["finished"] = True
    
    if message:
        await send_message_clean(
            user_id,
            f"🎉 <b>ПРОДАНО!</b>\n\n"
            f"📦 {item_name}\n💰 Цена: {final_price}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽\n⭐ Репутация: {p['reputation']}/100"
        )
    
    return profit

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_code = args[1][4:]
        referrer_id = None
        for uid in referral_data:
            if generate_ref_code(uid) == ref_code: referrer_id = uid; break
        if referrer_id and referrer_id != str(user_id) and user_id not in referral_data[referrer_id]["invited"]:
            referral_data[referrer_id]["invited"].append(user_id)
            save_json(REFERRAL_FILE, dict(referral_data))
            if int(referrer_id) in players: players[int(referrer_id)]["balance"] += 500
            try:
                await bot.send_message(int(referrer_id), f"🎉 <b>НОВЫЙ РЕФЕРАЛ!</b>\n\n💰 +500₽\n👥 Всего: {len(referral_data[referrer_id]['invited'])}", parse_mode="HTML")
            except: pass
    
    p = players.get(user_id)
    await delete_user_messages(user_id)
    
    if p and p.get("day", 0) > 0:
        await show_welcome_back(message, user_id, p)
    else:
        await show_welcome_new(message, user_id)

async def show_welcome_new(message: types.Message, user_id: int):
    text = (
        "🎮 <b>ДОБРО ПОЖАЛОВАТЬ В RESELL TYCOON!</b>\n\n"
        "Ты — перекупщик. Цель: 5 000₽ → 50 000₽.\n\n"
        "🏭 • Закупайся у поставщиков\n"
        "📱 • Публикуй товары на Авито\n"
        "💬 • Общайся с покупателями в чате\n"
        "📈 • Следи за спросом\n"
        "⭐ • Зарабатывай репутацию\n\n"
        "👥 Приглашай друзей — +500₽!\n\n"
        "Готов?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
        [InlineKeyboardButton(text="📖 Как играть?", callback_data="how_to_play")],
        [InlineKeyboardButton(text="🔗 Рефералы", callback_data="ref_info")],
        [InlineKeyboardButton(text="👑 VIP", callback_data="vip_info")],
    ])
    await send_message_clean(user_id, text, reply_markup=kb)

async def show_welcome_back(message: types.Message, user_id: int, p: dict):
    rep = get_user_rep(user_id)
    level = get_rep_level(rep["score"])
    vip = is_vip(user_id)
    text = (
        f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n\n"
        f"📅 День: {p['day']}\n💰 Баланс: {p['balance']}₽\n"
        f"📦 Товаров: {len(p['inventory'])} шт.\n"
        f"📋 Продано: {p['items_sold']} шт.\n"
        f"⭐ Репутация: {level['name']}\n"
        f"{'👑 VIP!' if vip else ''}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
        [InlineKeyboardButton(text="🔄 НАЧАТЬ ЗАНОВО", callback_data="restart_game_confirm")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="action_stats_menu")],
        [InlineKeyboardButton(text="🔗 Рефералы", callback_data="action_ref")],
    ])
    await send_message_clean(user_id, text, reply_markup=kb)

@dp.message(Command('menu'))
async def menu_cmd(message: types.Message):
    user_id = message.from_user.id
    p = players.get(user_id)
    await delete_user_messages(user_id)
    if p and p.get("day", 0) > 0:
        await show_welcome_back(message, user_id, p)
    else:
        await show_welcome_new(message, user_id)

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await delete_user_messages(user_id)
    rep = get_user_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, rep["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0,
        "rep_mult": get_rep_multiplier(rep["score"]),
    }
    p = players[user_id]
    event = generate_daily_event(); p["current_event"] = event
    if event: apply_market_event(p, event)
    await state.set_state(GameState.playing)
    et = f"\n\n{event['text']}" if event else ""
    vip_txt = "\n👑 VIP!" if is_vip(user_id) else ""
    demand = format_demand(p)
    await send_message_clean(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5000₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=get_main_keyboard())

@dp.message(Command('ref'))
async def ref_cmd(message: types.Message):
    user_id = message.from_user.id
    await delete_user_messages(user_id)
    link = get_ref_link(user_id)
    count = len(referral_data[str(user_id)]["invited"])
    vip_user = is_vip(user_id)
    vip_txt = "\n👑 Ты в ТОП-3! VIP открыт!" if vip_user else ""
    await send_message_clean(user_id, f"🔗 <b>ТВОЯ ССЫЛКА:</b>\n<code>{link}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽{vip_txt}")

@dp.message(Command('rep'))
async def rep_cmd(message: types.Message):
    user_id = message.from_user.id
    await delete_user_messages(user_id)
    p = players.get(user_id)
    pd = {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]} if p else None
    new_ach = check_achievements(user_id, pd)
    user = get_user_rep(user_id)
    level = get_rep_level(user["score"])
    card = f"🏆 <b>РЕПУТАЦИЯ: {level['name']}</b>\n📊 Очки: {user['score']}/100\n📦 Продаж: {user['total_sales']}\n💰 Прибыль: {user['total_profit']}₽"
    if new_ach: card += "\n\n🎉 <b>НОВЫЕ!</b>\n" + "\n".join(f"{a['name']}" for a in new_ach)
    await send_message_clean(user_id, card)

# ==================== ОБРАБОТКА ЧАТА С НЕЙРОКЛИЕНТАМИ ====================
@dp.callback_query(F.data.startswith("neuro_reply_"))
async def neuro_reply_btn(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    
    if chat_key not in active_chats or active_chats[chat_key]["finished"]:
        await callback.answer("Диалог завершён")
        return
    
    chat = active_chats[chat_key]
    
    await send_message_clean(
        user_id,
        f"💬 <b>ДИАЛОГ С ПОКУПАТЕЛЕМ #{buyer_id}</b>\n"
        f"📦 {chat['item']}\n"
        f"💰 Твоя цена: {chat['price']}₽ | Предложение: {chat['offer']}₽\n\n"
        f"<i>Напиши свой ответ в чат. Торгуйся, убеждай, предлагай свою цену!</i>"
    )
    
    await state.set_state(GameState.playing)
    await callback.answer()

@dp.message(StateFilter(GameState.playing))
async def handle_neuro_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    # Сохраняем для удаления
    pending_messages[user_id].append(message.message_id)
    
    # Ищем активный диалог
    active_dialog = None
    dialog_key = None
    for key, chat in active_chats.items():
        if chat["user_id"] == user_id and not chat["finished"]:
            active_dialog = chat
            dialog_key = key
            break
    
    if not active_dialog:
        return
    
    chat = active_dialog
    chat["history"].append({"role": "user", "content": text})
    chat["round"] += 1
    
    if chat["round"] > chat["max_rounds"]:
        chat["finished"] = True
        msgs = {"angry": "Всё, надоело ждать. Я пошёл.", "kind": "Ладно, подумаю ещё. Спасибо за ответы!", "sly": "Хорошо, удачи. Поищу другого продавца."}
        end_msg = msgs.get(chat["client_type"], "Пока.")
        if dialog_key in remind_timers:
            remind_timers[dialog_key].cancel()
        await send_message_clean(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {end_msg}\n\n⚠️ Диалог завершён.")
        return
    
    # DeepSeek
    try:
        resp = client_openai.chat.completions.create(
            model="deepseek-chat", messages=chat["history"],
            temperature=0.9, max_tokens=200
        )
        ai_msg = resp.choices[0].message.content
    except:
        fallbacks = {
            "angry": [f"Короче, {chat['offer']}₽. Берёшь или нет?!"],
            "kind": [f"Ну пожалуйста, может уступите? У меня только {chat['offer']}₽."],
            "sly": [f"Рынок падает. {chat['offer']}₽ — хорошая цена."]
        }
        ai_msg = random.choice(fallbacks.get(chat["client_type"], [f"Моё предложение {chat['offer']}₽."]))
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    # Проверка завершения
    finished = False; result = None
    ml = ai_msg.lower()
    agree_words = ["беру", "договорились", "по рукам", "забираю", "согласен", "давай", "идёт"]
    for w in agree_words:
        if w in ml and "?" not in ml: finished = True; result = "sold"; break
    if not finished:
        decline_words = ["нет", "не буду", "ушёл", "пошёл", "пока", "до свидания", "удачи"]
        for w in decline_words:
            if w in ml: finished = True; result = "lost"; break
    
    if finished:
        chat["finished"] = True
        if dialog_key in remind_timers:
            remind_timers[dialog_key].cancel()
        if result == "sold":
            await complete_neuro_sale(user_id, chat["buyer_id"], message)
        else:
            await send_message_clean(user_id, f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}\n\n👋 Клиент ушёл.")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ПРОДОЛЖИТЬ ДИАЛОГ", callback_data=f"neuro_reply_{user_id}_{chat['buyer_id']}"),
             InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"neuro_decline_{user_id}_{chat['buyer_id']}")],
        ])
        await send_message_clean(
            user_id,
            f"👤 <b>Покупатель #{chat['buyer_id']}:</b> {ai_msg}\n\n"
            f"<i>Раунд {chat['round']}/{chat['max_rounds']} | Его предложение: {chat['offer']}₽</i>\n\n"
            f"Напиши ответ или нажми кнопку:",
            reply_markup=kb
        )

@dp.callback_query(F.data.startswith("neuro_accept_"))
async def neuro_accept_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    
    if chat_key not in active_chats or active_chats[chat_key]["finished"]:
        return await callback.answer("Диалог завершён")
    
    chat = active_chats[chat_key]
    chat["history"].append({"role": "user", "content": f"Согласен на {chat['offer']}₽"})
    chat["finished"] = True
    
    await complete_neuro_sale(user_id, buyer_id, callback.message)
    await callback.answer("Продано!")

@dp.callback_query(F.data.startswith("neuro_decline_"))
async def neuro_decline_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    
    if chat_key in active_chats:
        active_chats[chat_key]["finished"] = True
        if chat_key in remind_timers:
            remind_timers[chat_key].cancel()
    
    await send_message_clean(user_id, "❌ Вы отказались. Клиент ушёл.")
    await callback.answer()

# ==================== ОСТАЛЬНЫЕ CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    rep = get_user_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, rep["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0,
        "rep_mult": get_rep_multiplier(rep["score"]),
    }
    p = players[user_id]
    event = generate_daily_event(); p["current_event"] = event
    if event: apply_market_event(p, event)
    await state.set_state(GameState.playing)
    et = f"\n\n{event['text']}" if event else ""
    vip_txt = "\n👑 VIP!" if is_vip(user_id) else ""
    demand = format_demand(p)
    await edit_message_clean(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n\n🌟 День 1\n💰 5 000₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nЦель: 50 000₽!", reply_markup=get_main_keyboard())
    await callback.answer("🚀")

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    demand = format_demand(p)
    await edit_message_clean(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=get_main_keyboard())
    await callback.answer("🎮")

@dp.callback_query(F.data == "restart_game_confirm")
async def restart_game_confirm_btn(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, СБРОСИТЬ", callback_data="restart_game_yes")],
        [InlineKeyboardButton(text="❌ НЕТ", callback_data="continue_game")],
    ])
    await edit_message_clean(callback.message, "⚠️ <b>СБРОСИТЬ?</b>\n\nБаланс и инвентарь потеряются!\nРепутация и рефералы сохранятся.", reply_markup=kb)

@dp.callback_query(F.data == "restart_game_yes")
async def restart_game_yes_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id in players: del players[user_id]
    await start_new_game_btn(callback, state)

@dp.callback_query(F.data == "how_to_play")
async def how_to_play_btn(callback: CallbackQuery):
    text = (
        "📖 <b>КАК ИГРАТЬ:</b>\n\n"
        "1️⃣ <b>Закупка</b> — купи у поставщиков\n"
        "2️⃣ <b>Публикация</b> — жми «📱 Опубликовать»\n"
        "3️⃣ <b>Чат</b> — жми «💬 ОТВЕТИТЬ» и пиши ответ\n"
        "   • Торгуйся словами как с живым!\n"
        "   • Убеждай, предлагай цену\n"
        "   • Характер не виден — узнавай по общению\n"
        "4️⃣ <b>Репутация</b> — растёт от продаж\n"
        "5️⃣ <b>Рефералы</b> — /ref, +500₽ за друга"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_welcome")],
    ])
    await edit_message_clean(callback.message, text, reply_markup=kb)

@dp.callback_query(F.data == "ref_info")
async def ref_info_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    link = get_ref_link(user_id)
    text = f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{link}</code>\n\n💰 +500₽ за друга\n👑 Топ-3 — VIP"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_welcome")],
    ])
    await edit_message_clean(callback.message, text, reply_markup=kb)

@dp.callback_query(F.data == "vip_info")
async def vip_info_btn(callback: CallbackQuery):
    text = "👑 <b>VIP:</b>\n\nТоп-3 реферера — PremiumStock!\n🌟 Цены +5%\n🛡️ 0% кидалова\n⭐ Рейтинг 10/10"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_welcome")],
    ])
    await edit_message_clean(callback.message, text, reply_markup=kb)

@dp.callback_query(F.data == "back_to_welcome")
async def back_to_welcome_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if p and p.get("day", 0) > 0:
        await show_welcome_back(callback.message, user_id, p)
    else:
        await show_welcome_new(callback.message, user_id)

@dp.callback_query(F.data == "action_stats_menu")
async def stats_menu_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if not p: return await callback.answer("Нет игры")
    ref_n = len(referral_data[str(user_id)]["invited"])
    vip = "👑 ДА" if is_vip(user_id) else "❌ Нет"
    text = f"📊 <b>СТАТИСТИКА:</b>\n\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Заработано: {p['total_earned']}₽\n👥 Рефералы: {ref_n}\n👑 VIP: {vip}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="back_to_welcome")],
    ])
    await edit_message_clean(callback.message, text, reply_markup=kb)

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = []
    for s in supps:
        kb.append([InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"supplier_{supps.index(s)}")])
    kb.append([InlineKeyboardButton(text="🔙 Меню", callback_data="action_back")])
    vip_txt = "\n👑 VIP доступен!" if is_vip(user_id) else ""
    await edit_message_clean(callback.message, f"🏭 <b>ПОСТАВЩИКИ:</b>{vip_txt}\nРейтинг ↑ = надёжнее.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("supplier_"), StateFilter(GameState.playing))
async def show_supplier_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]
    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    kb = []
    for i, it in enumerate(items):
        kb.append([InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {get_item_price(it['base_price'], sup)}₽", callback_data=f"buyitem_{i}")])
    kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"supplier_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 Поставщики", callback_data="action_buy")])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")])
    await state.update_data(current_supplier_idx=idx, supplier_items=items)
    await edit_message_clean(callback.message, f"{sup['emoji']} <b>{sup['name']}</b>\n⭐{sup['rating']}/10 | ⚠️Кид:{sup['scam_chance']}%\nВыбери:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("buyitem_"), StateFilter(GameState.playing))
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1])
    sup_idx = data.get("current_supplier_idx", 0)
    items = data.get("supplier_items", [])
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[sup_idx]
    if item_idx >= len(items): return await callback.answer("Ошибка")
    item = items[item_idx]
    p = get_player(user_id)
    price = int(get_item_price(item["base_price"], sup) * p["rep_mult"]["supplier_discount"])
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    eff_scam = int(sup["scam_chance"] * p["rep_mult"]["scam_reduce"])
    if random.randint(1, 100) <= eff_scam:
        p["balance"] -= price; p["total_spent"] += price; p["scam_times"] += 1
        p["reputation"] = max(0, p["reputation"] - 5)
        add_rep(user_id, -5, f"Кинул {sup['name']}")
        await edit_message_clean(callback.message, f"💀 <b>КИНУЛИ!</b>\n-{price}₽ | Баланс: {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))
        return
    p["balance"] -= price; p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    market_price = get_market_price(item["base_price"], demand)
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": market_price, "base_price": item["base_price"]})
    if sup["rating"] >= 8: add_rep(user_id, 1, "Надёжный поставщик")
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_message_clean(callback.message, f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽\n📊 Рынок: ~{market_price}₽\n💼 Баланс: {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё", callback_data=f"supplier_{sup_idx}")], [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    if not p["inventory"]:
        return await edit_message_clean(callback.message, "📦 Инвентарь пуст.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 Закупиться", callback_data="action_buy")], [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        status = "📢 Опубликован" if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == it["name"] else "📱 Опубликовать"
        kb.append([InlineKeyboardButton(text=f"{it['name']} | Закуп:{it['buy_price']}₽ | ~{it['market_price']}₽ | {status}", callback_data=f"inventory_{i}")])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")])
    txt = "📦 <b>ИНВЕНТАРЬ:</b>\n" + "\n".join(f"{i+1}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"]))
    txt += "\n\nНажми на товар, чтобы опубликовать!"
    await edit_message_clean(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("inventory_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    item = p["inventory"][item_idx]
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item["name"]:
        return await callback.answer("Уже опубликован!")
    published_items[user_id] = {"item": item.copy(), "buyers_list": []}
    await edit_message_clean(callback.message, f"📢 <b>ОПУБЛИКОВАНО!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n\n⏳ Жди покупателей 1-3 мин...\nОни напишут в чат!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 Инвентарь", callback_data="action_inventory")], [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))
    asyncio.create_task(spawn_buyers(user_id))
    await callback.answer("Опубликовано!")

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    ref_n = len(referral_data[str(user_id)]["invited"])
    vip = "👑 ДА" if is_vip(user_id) else "❌ Нет"
    await edit_message_clean(callback.message, f"📊 <b>СТАТИСТИКА:</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Заработано: {p['total_earned']}₽\n👥 Рефералы: {ref_n}\n👑 VIP: {vip}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_rep")
async def rep_btn(callback: CallbackQuery):
    await rep_cmd(callback.message)

@dp.callback_query(F.data == "action_ref")
async def ref_btn(callback: CallbackQuery):
    await ref_cmd(callback.message)

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    demand_lines = []
    tips = []
    for cat, mult in p["market_demand"].items():
        if mult >= 1.5: emoji = "🔥"; status = "Ажиотаж!"; tips.append(f"💡 {cat} в хайпе — продавай дороже!")
        elif mult >= 1.2: emoji = "📈"; status = "Растёт"
        elif mult >= 0.8: emoji = "➡️"; status = "Стабильно"
        elif mult >= 0.5: emoji = "📉"; status = "Падает"; tips.append(f"⚠️ {cat} падает — покупай дёшево")
        else: emoji = "💀"; status = "Мёртвый"; tips.append(f"🚫 {cat} не покупай")
        demand_lines.append(f"{emoji} <b>{cat}</b>: x{mult:.1f} ({status})")
    event_text = f"\n\n📰 <b>Событие:</b>\n{p['current_event']['text']}" if p.get("current_event") else ""
    tips_text = "\n\n".join(tips) if tips else ""
    await edit_message_clean(callback.message, f"📊 <b>РЫНОК — День {p['day']}</b>\n\n" + "\n".join(demand_lines) + event_text + (f"\n\n💡 <b>Советы:</b>\n{tips_text}" if tips_text else ""), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    summary = f"🌙 <b>ИТОГИ ДНЯ {p['day']}</b>\n💰 Заработано: {p['stat_earned_today']}₽\n📋 Продано: {p['stat_sold_today']} шт.\n💼 Баланс: {p['balance']}₽"
    p["day"] += 1; p["stat_earned_today"] = 0; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = generate_daily_event(); p["current_event"] = event
    if event: apply_market_event(p, event)
    et = f"\n\n📰 {event['text']}" if event else ""
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
        et += "\n⚠️ Товары залежались — потеря в цене."
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    if user_id in published_items: published_items[user_id] = None
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    demand = format_demand(p)
    await edit_message_clean(callback.message, f"{summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.clear()
    if p["balance"] >= 50000: result = "🏆 <b>ПОБЕДА!</b>"
    elif p["balance"] <= 0: result = "💀 <b>БАНКРОТ!</b>"
    else: result = "🎮 Игра окончена."
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_message_clean(callback.message, f"{result}\n💰 {p['balance']}₽\n📦 Продаж: {p['items_sold']}\n\nРеальные продажи → {CHANNEL_LINK}\n/play — ещё раз", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё раз", callback_data="restart_game")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in players: del players[user_id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    demand = format_demand(p)
    await edit_message_clean(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\nВыбери:", reply_markup=get_main_keyboard())

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())