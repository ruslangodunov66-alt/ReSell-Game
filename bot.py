import random
import hashlib
import json
import os
import asyncio
import re
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
BOT_USERNAME = 'R-Game'
DEEPSEEK_API_KEY = "sk-8d6e9d7c39c84ec6a0ecba379674346d"

client_openai = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# ==================== ФАЙЛЫ ====================
REPUTATION_FILE = "reputation_data.json"
REFERRAL_FILE = "referrals.json"
LEARNING_FILE = "learning_progress.json"

# ==================== СОВЕТЫ ====================
GAME_TIPS = {
    "after_buy": [
        "💡 Купил? Сразу публикуй! Быстрее выставишь — быстрее продашь.",
        "💡 Не держи товар долго — теряет в цене, как в реальности.",
    ],
    "after_publish": [
        "💡 Пока ждёшь — закупай ещё. Не теряй время!",
    ],
    "during_chat": [
        "💡 Не соглашайся на первую цену — всегда есть пространство для торга.",
        "💡 Опиши товар подробно — это повышает доверие.",
    ],
    "after_sale": [
        "💡 Откладывай 30% прибыли на закуп нового товара.",
    ],
}

# ==================== ОБУЧЕНИЕ ====================
LESSONS = [
    {"id": 1, "title": "🚀 Основы товарного бизнеса", "text": "📚 <b>ОСНОВЫ ТОВАРКИ</b>\n\n<b>Товарный бизнес</b> — перепродажа вещей.\n\n<b>Где брать товар:</b>\n• Авито (б/у дешевле)\n• Оптовые рынки (Садовод)\n• Китай (Taobao, 1688)\n• Секонд-хенды\n\n<b>Как заработать:</b>\nКупил дешевле → продал дороже = прибыль\n\n💰 Старт: от 1000₽", "reward": 500},
    {"id": 2, "title": "📊 Анализ рынка", "text": "📚 <b>АНАЛИЗ РЫНКА</b>\n\n<b>Что продавать:</b>\n• Поищи на Авито — много объявлений?\n• Смотри проданные лоты\n\n<b>Сезонность:</b>\n• Осень — куртки, школа\n• Зима — пуховики\n• Весна — демисезон\n• Лето — футболки\n\n💡 Покупай дёшево, продавай когда спрос высокий!", "reward": 500},
    {"id": 3, "title": "🏭 Поставщики", "text": "📚 <b>ПОСТАВЩИКИ</b>\n\n<b>Как не попасть на кидалово:</b>\n• Проси отзывы\n• Начни с малого заказа\n• Проверь по чёрным спискам\n• Не вноси 100% предоплату\n\n⚠️ Слишком низкая цена = подозрительно!", "reward": 700},
    {"id": 4, "title": "💬 Общение с покупателями", "text": "📚 <b>ПРОДАЖИ</b>\n\n<b>Как продать дороже:</b>\n• Хорошие фото\n• Подробное описание\n• Быстрый ответ\n• Не груби\n\n💡 Ставь цену на 20% выше — будет пространство для торга.", "reward": 700},
    {"id": 5, "title": "📈 Продвижение", "text": "📚 <b>ПРОДВИЖЕНИЕ</b>\n\n<b>Бесплатно:</b>\n• Обновляй каждые 24ч\n• Ключевые слова\n\n<b>Платно:</b>\n• Продвижение от 50₽/день\n\n💡 5-10 объявлений = выше шанс продажи!", "reward": 1000},
]

# ==================== ПОСТАВЩИКИ ====================
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
    {"cat": "🎒 Аксессуары", "name": "Stüssy Tote Bag", "base_price": 1500},
    {"cat": "🎒 Аксессуары", "name": "New Era 59Fifty Cap", "base_price": 1200},
    {"cat": "👕 Худи", "name": "Supreme Box Logo", "base_price": 1800},
    {"cat": "🧥 Куртки", "name": "Stone Island Soft Shell", "base_price": 6000},
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

MARKET_EVENTS = [
    {"text": "📰 Хайп на джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — куртки в цене!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Кроссовки в тренде!", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Комиссия Авито 15%", "cat": None, "mult": 0.8},
    {"text": "📰 Аксессуары в тренде!", "cat": "🎒 Аксессуары", "mult": 1.6},
]

# ==================== НЕЙРОКЛИЕНТЫ (ЖИВЫЕ ПРОМПТЫ) ====================
CLIENT_TYPES = {
    "angry": {
        "system_prompt": (
            "Ты — покупатель на Авито. Ты РЕАЛЬНЫЙ ЧЕЛОВЕК, который хочет купить товар.\n\n"
            "ТВОЙ ХАРАКТЕР: Недоверчивый, прямой, иногда резкий, но без мата.\n"
            "Торгуешься жёстко, хочешь скидку 20-40%. Сомневаешься в качестве.\n\n"
            "КАК ОБЩАТЬСЯ: Задавай вопросы о товаре (состояние, размер, дефекты, почему продаёшь).\n"
            "Реагируй на ответы продавца. Если аргументы убедительные — можешь поднять цену.\n"
            "Если продавец хорошо описывает товар — смягчайся.\n"
            "Если продавец не идёт на уступки — можешь уйти.\n"
            "НЕ ПОВТОРЯЙ одни и те же фразы. Меняй предложение в зависимости от диалога.\n"
            "Используй живые выражения: 'слушай', 'смотри', 'ну ок', 'ладно'.\n"
            "ОТВЕЧАЙ КОРОТКО, 1-3 предложения, как в чате."
        ),
        "discount_range": (0.6, 0.8), "patience": 4, "remind_time": (120, 300)
    },
    "kind": {
        "system_prompt": (
            "Ты — покупатель на Авито. Ты РЕАЛЬНЫЙ ЧЕЛОВЕК, вежливый и приятный.\n\n"
            "ТВОЙ ХАРАКТЕР: Вежливый, используешь 'пожалуйста', 'спасибо'.\n"
            "Доверяешь продавцу, хочешь небольшую скидку 5-15%.\n"
            "Делаешь комплименты товару, искренне интересуешься.\n\n"
            "КАК ОБЩАТЬСЯ: Задавай вопросы (состояние, размер, можно померить?).\n"
            "Хвали товар: 'отличная вещь', 'давно искал'.\n"
            "Реагируй на ответы. Если продавец идёт навстречу — соглашайся.\n"
            "НЕ ПОВТОРЯЙ одни и те же фразы.\n"
            "ОТВЕЧАЙ КОРОТКО, 1-3 предложения, как в чате."
        ),
        "discount_range": (0.85, 0.95), "patience": 6, "remind_time": (180, 420)
    },
    "sly": {
        "system_prompt": (
            "Ты — покупатель на Авито, перекупщик. Ты РЕАЛЬНЫЙ ЧЕЛОВЕК, знаешь рынок.\n\n"
            "ТВОЙ ХАРАКТЕР: Опытный, знаешь цены. Хитрый, умеешь торговаться.\n"
            "Приводишь аргументы: 'я такие дешевле видел'. Можешь блефовать.\n"
            "Хочешь скидку 15-30%.\n\n"
            "КАК ОБЩАТЬСЯ: Задавай вопросы о товаре, сравнивай с рынком.\n"
            "Аргументируй свою цену. Если продавец убедителен — поднимай предложение.\n"
            "Реагируй на описание товара. Если видишь что товар реально хороший — признай это.\n"
            "НЕ ПОВТОРЯЙ одни и те же фразы.\n"
            "ОТВЕЧАЙ КОРОТКО, 1-3 предложения, как в чате."
        ),
        "discount_range": (0.7, 0.85), "patience": 5, "remind_time": (150, 360)
    }
}

# ==================== РЕПУТАЦИЯ ====================
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
shown_tips = defaultdict(set)
active_chat_for_user = {}

# ==================== ЗАГРУЗКА ====================
def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_all():
    global referral_data, rep_data, learning_data
    referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False}, load_json(REFERRAL_FILE, {}))
    rep_data = load_json(REPUTATION_FILE, {})
    learning_data = load_json(LEARNING_FILE, {})

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

# Кнопка меню для каждого сообщения
def menu_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")]
    ])

async def send_msg(user_id, text, parse_mode="HTML", reply_markup=None):
    await del_prev(user_id)
    await del_user_msgs(user_id)
    if reply_markup is None:
        reply_markup = menu_btn()
    msg = await bot.send_message(user_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    last_bot_message[user_id] = msg.message_id
    return msg

async def edit_msg(message, text, parse_mode="HTML", reply_markup=None):
    await del_user_msgs(message.chat.id)
    if reply_markup is None:
        reply_markup = menu_btn()
    try: await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except: pass

# ==================== РЕФЕРАЛЫ ====================
def gen_ref(user_id): return hashlib.md5(str(user_id).encode()).hexdigest()[:8]
def ref_link(user_id): return f"https://t.me/{BOT_USERNAME}?start=ref_{gen_ref(user_id)}"
def top_refs(limit=10):
    s = [(uid, len(d["invited"])) for uid, d in referral_data.items()]
    s.sort(key=lambda x: x[1], reverse=True)
    return s[:limit]
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

def add_rep(user_id, amount, reason=""):
    u = get_rep(user_id)
    u["score"] = max(-100, min(100, u["score"] + amount))
    u["rep_history"].append({"change": amount, "reason": reason, "total": u["score"]})
    save_json(REPUTATION_FILE, rep_data)
    return u["score"]

def rep_mult(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_ach(user_id, pd=None):
    u = get_rep(user_id)
    if pd:
        u["total_sales"] = pd.get("items_sold", 0)
        u["total_profit"] = pd.get("total_earned", 0)
        u["max_balance"] = max(u["max_balance"], pd.get("balance", 0))
    new_a = []
    for a in ACHIEVEMENTS:
        if a["id"] in u["achievements"]: continue
        earn = False
        if a["id"] == "first_sale" and u["total_sales"] >= 1: earn = True
        elif a["id"] == "seller_10" and u["total_sales"] >= 10: earn = True
        elif a["id"] == "profit_5000" and u["total_profit"] >= 5000: earn = True
        if earn:
            u["achievements"].append(a["id"])
            add_rep(user_id, a["reward"], f"Достижение: {a['name']}")
            new_a.append(a)
    save_json(REPUTATION_FILE, rep_data)
    return new_a

# ==================== ОБУЧЕНИЕ ====================
def get_learning(user_id):
    uid = str(user_id)
    if uid not in learning_data:
        learning_data[uid] = {"completed": [], "current": 1}
        save_json(LEARNING_FILE, learning_data)
    return learning_data[uid]

def complete_lesson(user_id, lesson_id):
    u = get_rep(user_id)
    l = get_learning(user_id)
    if lesson_id not in l["completed"]:
        l["completed"].append(lesson_id)
        u["lessons_completed"] = len(l["completed"])
        l["current"] = lesson_id + 1
        save_json(LEARNING_FILE, learning_data)
        save_json(REPUTATION_FILE, rep_data)
        lesson = next((ls for ls in LESSONS if ls["id"] == lesson_id), None)
        if lesson and user_id in players:
            players[user_id]["balance"] += lesson["reward"]
            add_rep(user_id, 3, f"Урок: {lesson['title']}")
        check_ach(user_id)
        return True
    return False

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        r = get_rep(user_id)
        rm = rep_mult(r["score"])
        players[user_id] = {
            "balance": 5000, "reputation": max(0, r["score"]),
            "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0,
            "items_sold": r["total_sales"], "scam_times": r["scam_survived"],
            "market_demand": {cat: 1.0 for cat in CATEGORIES},
            "current_event": None, "stat_earned_today": 0, "stat_sold_today": 0,
            "rep_mult": rm,
        }
    return players[user_id]

def item_price(base, sup): return int(base * sup["price_mult"])
def market_price(base, demand): return int(base * demand * random.uniform(0.9, 1.3))
def daily_event(): return random.choice(MARKET_EVENTS) if random.random() < 0.6 else None

def apply_event(p, event):
    if event["cat"]: p["market_demand"][event["cat"]] = max(0.3, min(3.0, p["market_demand"][event["cat"]] * event["mult"]))
    else:
        for cat in CATEGORIES: p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat] * event["mult"]))

def fmt_demand(p):
    lines = []
    for cat, mult in p["market_demand"].items():
        emoji = "🔥" if mult >= 1.5 else "📈" if mult >= 1.2 else "➡️" if mult >= 0.8 else "📉" if mult >= 0.5 else "💀"
        lines.append(f"{emoji} {cat}: x{mult:.1f}")
    return "\n".join(lines)

def get_active_buyers_count(user_id):
    return sum(1 for c in active_chats.values() if c["user_id"] == user_id and not c["finished"])

def main_kb(user_id=None):
    buyers_count = get_active_buyers_count(user_id) if user_id else 0
    chat_label = f"💬 ЧАТЫ ({buyers_count})" if buyers_count > 0 else "💬 ЧАТЫ"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text=chat_label, callback_data="action_chats"),
         InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats"),
         InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep_menu")],
        [InlineKeyboardButton(text="📈 СПРОС", callback_data="action_demand"),
         InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref_menu")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])

# ==================== НЕЙРОКЛИЕНТЫ ====================
def first_msg(client_type, item_name, price, offer):
    msgs = {
        "angry": [
            f"Здравствуйте! По поводу {item_name}. Расскажите подробнее о состоянии? И почему цена {price}₽?",
            f"Привет! {item_name} интересует. А что по состоянию? {price}₽ — это окончательная цена?",
        ],
        "kind": [
            f"Добрый день! Очень заинтересовал {item_name}. Расскажите о состоянии пожалуйста?",
            f"Здравствуйте! {item_name} — то что ищу! Можете рассказать подробнее?",
        ],
        "sly": [
            f"Привет! По {item_name}. Что по состоянию? И готовы ли обсуждать цену?",
            f"Здорово! {item_name} интересует. Расскажи что да как, и по цене может договоримся.",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

async def send_buyer(user_id, buyer_id, client_type, item_name, price, is_reminder=False):
    client = CLIENT_TYPES[client_type]
    chat_key = f"{user_id}_{buyer_id}"
    
    if not is_reminder:
        rm = rep_mult(get_rep(user_id)["score"])
        discount = random.uniform(*client["discount_range"]) + rm["haggle_bonus"]
        discount = max(0.3, min(0.95, discount))
        offer = int(price * discount)
        offer = (offer // 100) * 100 + 99
        if offer < 100: offer = price // 2
        
        msg = first_msg(client_type, item_name, price, offer)
        
        active_chats[chat_key] = {
            "user_id": user_id, "buyer_id": buyer_id, "client_type": client_type,
            "item": item_name, "price": price, "offer": offer,
            "history": [{"role": "system", "content": client["system_prompt"]}, {"role": "assistant", "content": msg}],
            "round": 1, "max_rounds": client["patience"], "finished": False,
            "reminders_sent": 0, "max_reminders": 2
        }
        
        txt = f"📩 <b>НОВОЕ СООБЩЕНИЕ</b>\n\n👤 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n\n💬 {msg}\n\n<i>Ответь на это сообщение чтобы начать диалог</i>"
        
        await send_msg(user_id, txt)
        
        if client["remind_time"]:
            task = asyncio.create_task(do_remind(user_id, buyer_id, random.randint(*client["remind_time"])))
            remind_timers[chat_key] = task
    else:
        chat = active_chats.get(chat_key)
        if not chat or chat["finished"]: return
        msg = f"Извините, я всё ещё жду ответ по {item_name}. Вы тут?"
        chat["history"].append({"role": "assistant", "content": msg})
        chat["reminders_sent"] += 1
        
        await send_msg(user_id, f"🔔 <b>Покупатель #{buyer_id}</b>\n📦 {item_name}\n\n💬 {msg}")
        
        if chat["reminders_sent"] < chat["max_reminders"]:
            task = asyncio.create_task(do_remind(user_id, buyer_id, random.randint(*client["remind_time"])))
            remind_timers[chat_key] = task

async def do_remind(user_id, buyer_id, delay):
    await asyncio.sleep(delay)
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if chat and not chat["finished"] and chat["reminders_sent"] < chat["max_reminders"]:
        await send_buyer(user_id, buyer_id, chat["client_type"], chat["item"], chat["price"], is_reminder=True)

async def spawn_buyers(user_id):
    await asyncio.sleep(random.randint(60, 180))
    if user_id not in published_items or not published_items[user_id]: return
    pub = published_items[user_id]
    item = pub["item"]
    rm = rep_mult(get_rep(user_id)["score"])
    n = random.randint(1, 3)
    if rm["haggle_bonus"] > 0.1: n = min(3, n + 1)
    types = random.choices(list(CLIENT_TYPES.keys()), k=n)
    
    await send_msg(user_id, f"📱 <b>ОБЪЯВЛЕНИЕ РАБОТАЕТ!</b>\n\n📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n👥 Пишут: <b>{n}</b> чел.\n\n<i>Отвечай на сообщения покупателей!</i>")
    
    pub["buyers_list"] = []
    for i, bt in enumerate(types):
        await asyncio.sleep(random.randint(5, 20))
        bid = i + 1
        pub["buyers_list"].append({"id": bid, "type": bt, "active": True})
        await send_buyer(user_id, bid, bt, item["name"], item["market_price"])

async def complete_sale(user_id, buyer_id, message=None):
    chat_key = f"{user_id}_{buyer_id}"
    chat = active_chats.get(chat_key)
    if not chat: return None
    
    p = get_player(user_id)
    item_name = chat["item"]
    final = chat["offer"]
    
    sold = None
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item_name:
        sold = published_items[user_id]["item"]
        published_items[user_id] = None
    
    for i, inv in enumerate(p["inventory"]):
        if inv["name"] == item_name:
            sold = p["inventory"].pop(i)
            break
    
    if not sold:
        if message: await send_msg(user_id, "❌ Товар не найден.")
        return None
    
    profit = final - sold["buy_price"]
    p["balance"] += final
    p["total_earned"] += profit
    p["items_sold"] += 1
    p["stat_earned_today"] += profit
    p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + 5)
    
    add_rep(user_id, random.randint(2, 5), f"Продажа: {item_name}")
    if chat["client_type"] == "angry": get_rep(user_id)["angry_deals"] += 1
    
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    
    if chat_key in remind_timers:
        remind_timers[chat_key].cancel()
        del remind_timers[chat_key]
    
    chat["finished"] = True
    if user_id in active_chat_for_user: del active_chat_for_user[user_id]
    
    if message:
        await send_msg(user_id, f"🎉 <b>ПРОДАНО!</b>\n\n📦 {item_name}\n💰 Цена: {final}₽\n💵 Прибыль: {profit}₽\n💼 Баланс: {p['balance']}₽")
    
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
            if gen_ref(uid) == ref_code: referrer_id = uid; break
        if referrer_id and referrer_id != str(user_id) and user_id not in referral_data[referrer_id]["invited"]:
            referral_data[referrer_id]["invited"].append(user_id)
            save_json(REFERRAL_FILE, dict(referral_data))
            if int(referrer_id) in players: players[int(referrer_id)]["balance"] += 500
            try: await bot.send_message(int(referrer_id), "🎉 Новый реферал! +500₽", parse_mode="HTML")
            except: pass
    
    p = players.get(user_id)
    await del_user_msgs(user_id)
    
    if p and p.get("day", 0) > 0:
        r = get_rep(user_id); lvl = rep_level(r["score"]); vip = is_vip(user_id)
        txt = f"👋 <b>С ВОЗВРАЩЕНИЕМ!</b>\n\n📅 День {p['day']} | 💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])} | 📋 Продано: {p['items_sold']}\n⭐ {lvl}{' | 👑 VIP' if vip else ''}"
        await send_msg(user_id, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")],
            [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")],
        ]))
    else:
        l = get_learning(user_id)
        await send_msg(user_id, f"🎮 <b>RESELL TYCOON</b>\n\nНаучись зарабатывать на перепродаже!\n\n📚 Уроков: {len(l['completed'])}/{len(LESSONS)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 ОБУЧЕНИЕ", callback_data="action_learn")],
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ИГРУ", callback_data="start_new_game")],
            [InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="ref_info")],
        ]))

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    r = get_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, r["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": r["total_sales"], "scam_times": r["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0, "rep_mult": rep_mult(r["score"]),
    }
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    et = f"\n\n📰 {event['text']}" if event else ""
    vip_txt = "\n👑 VIP!" if is_vip(user_id) else ""
    demand = fmt_demand(p)
    await send_msg(user_id, f"🌟 <b>ДЕНЬ 1</b>\n💰 5 000₽{vip_txt}{et}\n\n📊 <b>СПРОС:</b>\n{demand}\n\n👇 1. 🏭 Закупись → 2. 📦 Инвентарь → 3. Опубликуй → 4. 💬 Отвечай!", reply_markup=main_kb(user_id))

# ==================== ОСНОВНОЙ ЧАТ С ПОКУПАТЕЛЯМИ ====================
@dp.message(StateFilter(GameState.playing))
async def handle_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    pending_messages[user_id].append(message.message_id)
    
    # Проверяем активный чат
    if user_id in active_chat_for_user:
        chat_key = active_chat_for_user[user_id]
        if chat_key in active_chats and not active_chats[chat_key]["finished"]:
            await process_chat_message(user_id, chat_key, text, message)
            return
    
    # Ищем любой открытый диалог
    for key, chat in active_chats.items():
        if chat["user_id"] == user_id and not chat["finished"]:
            await process_chat_message(user_id, key, text, message)
            return

async def process_chat_message(user_id, chat_key, text, message):
    chat = active_chats[chat_key]
    buyer_id = chat["buyer_id"]
    client_type = chat["client_type"]
    client = CLIENT_TYPES[client_type]
    
    chat["history"].append({"role": "user", "content": text})
    chat["round"] += 1
    
    if chat["round"] > chat["max_rounds"]:
        chat["finished"] = True
        msgs = {"angry": "Всё, мне надоело. Удачи.", "kind": "Ладно, извините. Всего доброго!", "sly": "Понял, не договоримся. Поищу другого."}
        if chat_key in remind_timers: remind_timers[chat_key].cancel()
        if user_id in active_chat_for_user: del active_chat_for_user[user_id]
        await send_msg(user_id, f"👤 <b>Покупатель #{buyer_id}:</b> {msgs.get(client_type, 'Пока.')}\n\n⚠️ Диалог завершён.")
        return
    
    # Запрос к DeepSeek
    try:
        system_prompt = client["system_prompt"] + f"\n\nКонтекст диалога:\n- Товар: {chat['item']}\n- Цена продавца: {chat['price']}₽\n- Твоё предложение: {chat['offer']}₽\n- Раунд диалога: {chat['round']}/{chat['max_rounds']}\n\nТы должен вести ЕСТЕСТВЕННЫЙ диалог. Задавай вопросы о товаре. Реагируй на ответы продавца. Меняй цену если аргументы убедительные. Не повторяйся."
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat["history"][-8:])
        
        resp = client_openai.chat.completions.create(
            model="deepseek-chat", messages=messages, temperature=0.95, max_tokens=250
        )
        ai_msg = resp.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek error: {e}")
        fallbacks = {
            "angry": [f"Слушай, {chat['offer']}₽ — это моя цена. Но расскажи про состояние, может передумаю.", f"Я серьёзно. {chat['offer']}₽. Если товар реально хороший — могу чуть добавить."],
            "kind": [f"Понимаю. А можно чуть подробнее про товар? Может я готов буду чуть больше предложить.", f"Хорошо, я подумаю. {chat['offer']}₽ — это пока мой максимум."],
            "sly": [f"Слушай, рынок я знаю. Но опиши товар детальнее — может я и подниму цену.", f"Ладно, не буду спорить. Расскажи что там по состоянию?"],
        }
        ai_msg = random.choice(fallbacks.get(client_type, [f"Расскажите подробнее о товаре."]))
    
    chat["history"].append({"role": "assistant", "content": ai_msg})
    
    # Проверяем новую цену от клиента
    prices = re.findall(r'(\d{3,5})₽', ai_msg)
    for p in prices:
        new_price = int(p)
        if chat["offer"] < new_price <= chat["price"]:
            chat["offer"] = new_price
    
       # Проверка завершения диалога
    finished = False; result = None
    ml = ai_msg.lower()
    
    # Согласие от клиента
    agree_words = ["беру", "договорились", "по рукам", "забираю", "согласен", "давай", "идёт"]
    for w in agree_words:
        if w in ml and "?" not in ml: 
            finished = True; result = "sold"; break
    
    # Игрок соглашается продать по предложенной цене
    user_agree = ["продано", "продаю", "согласен", "договорились", "по рукам", "забирай", "отдаю", "продам", "бери"]
    for w in user_agree:
        if w in text.lower():
            finished = True; result = "sold"
            # Фиксируем цену которую предложил клиент
            ai_msg = f"Отлично! Тогда договорились на {chat['offer']}₽. Когда можно забрать?"
            chat["history"].append({"role": "assistant", "content": ai_msg})
            break
    
    # Отказ
    if not finished:
        decline_words = ["нет", "не буду", "ушёл", "пошёл", "пока", "до свидания", "удачи", "я пошёл"]
        for w in decline_words:
            if w in ml: 
                finished = True; result = "lost"; break

# ==================== ВКЛАДКА ЧАТЫ ====================
@dp.callback_query(F.data == "action_chats", StateFilter(GameState.playing))
async def show_chats(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_list = [(k, c) for k, c in active_chats.items() if c["user_id"] == user_id and not c["finished"]]
    
    if not active_list:
        return await edit_msg(callback.message, "💬 <b>ЧАТЫ</b>\n\nНет активных диалогов.\nОпубликуй товар в 📦 Инвентаре!")
    
    txt = f"💬 <b>ЧАТЫ ({len(active_list)}):</b>\n\n"
    kb = []
    for key, chat in active_list:
        status = "⏳ Ждёт" if chat["round"] == 1 else f"💬 Диалог ({chat['round']}/{chat['max_rounds']})"
        txt += f"👤 <b>#{chat['buyer_id']}</b> | 📦 {chat['item']}\n💰 {chat['offer']}₽ | {status}\n\n"
        kb.append([InlineKeyboardButton(text=f"👤 Покупатель #{chat['buyer_id']} — {chat['item']}", callback_data=f"open_chat_{user_id}_{chat['buyer_id']}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("open_chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[2]); buyer_id = int(parts[3])
    chat_key = f"{user_id}_{buyer_id}"
    
    if chat_key not in active_chats or active_chats[chat_key]["finished"]:
        await callback.answer("Диалог завершён"); return
    
    chat = active_chats[chat_key]
    active_chat_for_user[user_id] = chat_key
    await state.set_state(GameState.playing)
    
    await send_msg(user_id, f"💬 <b>ЧАТ С ПОКУПАТЕЛЕМ #{buyer_id}</b>\n\n📦 {chat['item']}\n💰 Твоя цена: {chat['price']}₽ | Предложение: {chat['offer']}₽\n\n<i>Пиши сообщения — покупатель ответит!</i>")
    await callback.answer("Чат открыт!")

# ==================== РЕПУТАЦИЯ И РЕФЕРАЛЫ (ИСПРАВЛЕНО) ====================
@dp.callback_query(F.data == "action_rep_menu")
async def rep_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = players.get(user_id)
    pd = {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]} if p else None
    new_a = check_ach(user_id, pd)
    u = get_rep(user_id)
    lvl = rep_level(u["score"])
    bar = "█" * int((u["score"]+100)/200*10) + "░" * (10-int((u["score"]+100)/200*10))
    txt = f"🏆 <b>РЕПУТАЦИЯ: {lvl}</b>\n📊 [{bar}] {u['score']}/100\n\n📦 Продаж: {u['total_sales']}\n💰 Прибыль: {u['total_profit']}₽"
    if new_a: txt += "\n\n🎉 <b>НОВЫЕ!</b>\n" + "\n".join(f"{a['name']}" for a in new_a)
    await edit_msg(callback.message, txt)

@dp.callback_query(F.data == "action_ref_menu")
async def ref_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    link = ref_link(user_id)
    count = len(referral_data[str(user_id)]["invited"])
    vip = "👑 Ты в ТОП-3! VIP!" if is_vip(user_id) else ""
    await edit_msg(callback.message, f"🔗 <b>РЕФЕРАЛЫ:</b>\n\n<code>{link}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽\n{vip}")

# ==================== ОСТАЛЬНЫЕ CALLBACK-ОБРАБОТЧИКИ (СОКРАЩЁННЫЕ) ====================
@dp.callback_query(F.data == "start_new_game")
async def start_new_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    r = get_rep(user_id)
    players[user_id] = {
        "balance": 5000, "reputation": max(0, r["score"]), "inventory": [],
        "day": 1, "total_earned": 0, "total_spent": 0,
        "items_sold": r["total_sales"], "scam_times": r["scam_survived"],
        "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
        "stat_earned_today": 0, "stat_sold_today": 0, "rep_mult": rep_mult(r["score"]),
    }
    p = players[user_id]
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    await state.set_state(GameState.playing)
    et = f"\n\n📰 {event['text']}" if event else ""
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"🚀 <b>ИГРА НАЧАЛАСЬ!</b>\n🌟 День 1 | 💰 5 000₽{et}\n\n📊 <b>СПРОС:</b>\n{demand}", reply_markup=main_kb(user_id))
    await callback.answer("🚀")

@dp.callback_query(F.data == "continue_game")
async def continue_game_btn(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if not p: return await callback.answer("Нет игры!")
    await state.set_state(GameState.playing)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{et}\n\n📊 <b>СПРОС:</b>\n{demand}", reply_markup=main_kb(user_id))
    await callback.answer("🎮")

@dp.callback_query(F.data == "action_learn")
async def learn_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    l = get_learning(user_id)
    kb = []
    for lesson in LESSONS:
        done = lesson["id"] in l["completed"]
        kb.append([InlineKeyboardButton(text=f"{'✅' if done else '📖'} {lesson['title']}", callback_data=f"lesson_{lesson['id']}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="back_to_start")])
    await edit_msg(callback.message, f"📚 <b>ОБУЧЕНИЕ</b>\nПройдено: {len(l['completed'])}/{len(LESSONS)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: CallbackQuery):
    user_id = callback.from_user.id
    lesson_id = int(callback.data.split("_")[1])
    lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
    if not lesson: return await callback.answer("Не найден")
    l = get_learning(user_id)
    done = lesson_id in l["completed"]
    kb = []
    if not done: kb.append([InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ (+₽)", callback_data=f"complete_lesson_{lesson_id}")])
    kb.append([InlineKeyboardButton(text="🔙 К УРОКАМ", callback_data="action_learn")])
    txt = lesson["text"] + (f"\n\n💰 +{lesson['reward']}₽" if not done else "\n✅ Пройден!")
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("complete_lesson_"))
async def complete_lesson_btn(callback: CallbackQuery):
    if complete_lesson(callback.from_user.id, int(callback.data.split("_")[2])):
        await callback.answer("Урок пройден!")
        await learn_btn(callback)
    else:
        await callback.answer("Уже пройден")

@dp.callback_query(F.data == "ref_info")
async def ref_info(callback: CallbackQuery):
    await edit_msg(callback.message, f"🔗 Твоя ссылка:\n<code>{ref_link(callback.from_user.id)}</code>\n\n💰 +500₽ за друга")

@dp.callback_query(F.data == "back_to_start")
async def back_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = players.get(user_id)
    if p and p.get("day", 0) > 0:
        await edit_msg(callback.message, f"👋 <b>МЕНЮ</b>\n📅 День {p['day']} | 💰 {p['balance']}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 ПРОДОЛЖИТЬ", callback_data="continue_game")]]))
    else:
        await edit_msg(callback.message, "🎮 <b>RESELL TYCOON</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="start_new_game")]]))

@dp.callback_query(F.data == "action_buy", StateFilter(GameState.playing))
async def show_suppliers(callback: CallbackQuery):
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    kb = []
    for s in supps:
        kb.append([InlineKeyboardButton(text=f"{s['emoji']} {s['name']} | ⭐{s['rating']} | Кид:{s['scam_chance']}%", callback_data=f"sup_{supps.index(s)}")])
    kb.append([InlineKeyboardButton(text="🔙 МЕНЮ", callback_data="action_back")])
    vip_txt = "\n👑 VIP доступен!" if is_vip(user_id) else ""
    await edit_msg(callback.message, f"🏭 <b>ПОСТАВЩИКИ:</b>{vip_txt}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sup_"), StateFilter(GameState.playing))
async def show_items(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[idx]
    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    p = get_player(user_id)
    kb = []
    for i, it in enumerate(items):
        pr = int(item_price(it["base_price"], sup) * p["rep_mult"]["supplier_discount"])
        mp = market_price(it["base_price"], p["market_demand"].get(it["cat"], 1.0))
        kb.append([InlineKeyboardButton(text=f"{it['cat']} {it['name']} — {pr}₽ (~{mp}₽)", callback_data=f"bi_{i}")])
    kb.append([InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data=f"sup_{idx}")])
    kb.append([InlineKeyboardButton(text="🔙 К ПОСТАВЩИКАМ", callback_data="action_buy")])
    await state.update_data(sup_idx=idx, sup_items=items)
    await edit_msg(callback.message, f"{sup['emoji']} <b>{sup['name']}</b>\n{sup['desc']}\n⭐ {sup['rating']}/10 | ⚠️ Кид:{sup['scam_chance']}%", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("bi_"), StateFilter(GameState.playing))
async def buy_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1])
    sup_idx = data.get("sup_idx", 0)
    items = data.get("sup_items", [])
    user_id = callback.from_user.id
    supps = SUPPLIERS.copy()
    if is_vip(user_id): supps.insert(0, VIP_SUPPLIER)
    sup = supps[sup_idx]
    if item_idx >= len(items): return await callback.answer("Ошибка")
    item = items[item_idx]
    p = get_player(user_id)
    price = int(item_price(item["base_price"], sup) * p["rep_mult"]["supplier_discount"])
    if p["balance"] < price: return await callback.answer("❌ Мало денег!")
    if random.randint(1, 100) <= int(sup["scam_chance"] * p["rep_mult"]["scam_reduce"]):
        p["balance"] -= price; p["total_spent"] += price; p["scam_times"] += 1
        add_rep(user_id, -5, f"Кинул {sup['name']}")
        await edit_msg(callback.message, f"💀 <b>КИНУЛИ!</b>\n-{price}₽ | 💼 {p['balance']}₽")
        return
    p["balance"] -= price; p["total_spent"] += price
    mp = market_price(item["base_price"], p["market_demand"].get(item["cat"], 1.0))
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": mp, "base_price": item["base_price"]})
    if sup["rating"] >= 8: add_rep(user_id, 1, "Надёжный поставщик")
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽ | 📊 ~{mp}₽\n💼 Баланс: {p['balance']}₽\n\n👇 Зайди в 📦 ИНВЕНТАРЬ и опубликуй!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 В ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
    ]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    if not p["inventory"]:
        return await edit_msg(callback.message, "📦 <b>ПУСТО</b>\nЗакупись! 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ", callback_data="action_buy")]]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        pub = user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == it["name"]
        status = "📢 ОПУБЛИКОВАН" if pub else "📱 ОПУБЛИКОВАТЬ"
        kb.append([InlineKeyboardButton(text=f"{it['name']} | {it['buy_price']}₽ → ~{it['market_price']}₽ | {status}", callback_data=f"inv_{i}")])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    txt = "📦 <b>ИНВЕНТАРЬ:</b>\n\n" + "\n".join(f"{i+1}. {it['name']} | Закуп: {it['buy_price']}₽ | Рынок: ~{it['market_price']}₽" for i, it in enumerate(p["inventory"]))
    txt += "\n\n👇 Нажми на товар чтобы опубликовать!"
    await edit_msg(callback.message, txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("inv_"), StateFilter(GameState.playing))
async def publish_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_idx = int(callback.data.split("_")[1])
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Товар не найден")
    item = p["inventory"][item_idx]
    if user_id in published_items and published_items[user_id] and published_items[user_id]["item"]["name"] == item["name"]:
        return await callback.answer("Уже опубликован!")
    published_items[user_id] = {"item": item.copy(), "buyers_list": []}
    await edit_msg(callback.message, f"📢 <b>ОПУБЛИКОВАНО!</b>\n📦 {item['name']}\n💰 {item['market_price']}₽\n\n⏳ Жди 1-3 минуты — придут покупатели!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 ЧАТЫ", callback_data="action_chats")], [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")]]))
    asyncio.create_task(spawn_buyers(user_id))
    await callback.answer("Опубликовано!")

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await edit_msg(callback.message, f"📊 <b>СТАТИСТИКА:</b>\n💰 {p['balance']}₽\n📦 Товаров: {len(p['inventory'])}\n📅 День: {p['day']}\n📋 Продано: {p['items_sold']}\n💸 Прибыль: {p['total_earned']}₽")

@dp.callback_query(F.data == "action_demand", StateFilter(GameState.playing))
async def show_demand(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    lines = []
    for cat, mult in p["market_demand"].items():
        emoji = "🔥" if mult >= 1.5 else "📈" if mult >= 1.2 else "➡️" if mult >= 0.8 else "📉" if mult >= 0.5 else "💀"
        lines.append(f"{emoji} {cat}: x{mult:.1f}")
    et = f"\n\n📰 {p['current_event']['text']}" if p.get("current_event") else ""
    await edit_msg(callback.message, f"📊 <b>РЫНОК — День {p['day']}</b>\n\n"+"\n".join(lines)+et)

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    p["day"] += 1; p["stat_earned_today"] = 0; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = daily_event(); p["current_event"] = event
    if event: apply_event(p, event)
    et = f"\n\n📰 {event['text']}" if event else ""
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
        et += "\n⚠️ Залежавшиеся товары подешевели."
    if user_id in published_items: published_items[user_id] = None
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"☀️ <b>ДЕНЬ {p['day']}</b> | 💰 {p['balance']}₽{et}\n\n📊 <b>СПРОС:</b>\n{demand}", reply_markup=main_kb(user_id))

@dp.callback_query(F.data == "action_end", StateFilter(GameState.playing))
async def end_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.clear()
    if p["balance"] >= 50000: r = "🏆 <b>ПОБЕДА!</b>"
    elif p["balance"] <= 0: r = "💀 <b>БАНКРОТ!</b>"
    else: r = "🎮 Игра окончена."
    check_ach(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await edit_msg(callback.message, f"{r}\n💰 {p['balance']}₽\n/play — ещё раз", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 ЕЩЁ РАЗ", callback_data="restart_game")]]))

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: CallbackQuery):
    if callback.from_user.id in players: del players[callback.from_user.id]
    await callback.message.edit_text("🔄 Напиши /play")

@dp.callback_query(F.data == "action_back", StateFilter(GameState.playing))
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    et = f"\n\n{p['current_event']['text']}" if p.get("current_event") else ""
    demand = fmt_demand(p)
    await edit_msg(callback.message, f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{et}\n\n📊 <b>СПРОС:</b>\n{demand}", reply_markup=main_kb(user_id))

# ==================== МИНИ-ИГРА: ЗАРАБОТОК ====================
import time as time_module

# Хранилище для мини-игры
side_jobs = {}  # {user_id: {"type": str, "start_time": float, "reward": int, "duration": int, "done": bool}}

JOBS = [
    {"name": "📦 Расклейка объявлений", "description": "Расклеиваешь объявления по району. Платят немного, зато быстро.", "duration": 60, "reward": 200, "emoji": "📦"},
    {"name": "🚗 Доставка заказов", "description": "Развозишь заказы на велосипеде. Средний заработок.", "duration": 120, "reward": 500, "emoji": "🚗"},
    {"name": "💻 Фриланс (дизайн)", "description": "Делаешь логотип для клиента. Платят хорошо, но дольше.", "duration": 300, "reward": 1200, "emoji": "💻"},
    {"name": "🏪 Работа в магазине", "description": "Подменяешь продавца в стоке. Можно и товар присмотреть.", "duration": 180, "reward": 700, "emoji": "🏪"},
    {"name": "📸 Съёмка товаров", "description": "Фоткаешь вещи для других продавцов. Быстрые деньги.", "duration": 90, "reward": 350, "emoji": "📸"},
]

@dp.callback_query(F.data == "action_job", StateFilter(GameState.playing))
async def show_jobs(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    
    kb = []
    for job in JOBS:
        kb.append([InlineKeyboardButton(
            text=f"{job['emoji']} {job['name']} — {job['reward']}₽ ({job['duration']} сек)",
            callback_data=f"start_job_{JOBS.index(job)}"
        )])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    
    # Проверяем есть ли активная работа
    active_job = ""
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        job_data = side_jobs[user_id]
        elapsed = int(time_module.time() - job_data["start_time"])
        remaining = max(0, job_data["duration"] - elapsed)
        job = JOBS[job_data["type"]]
        active_job = f"\n\n⏳ <b>Активная работа:</b> {job['emoji']} {job['name']}\nОсталось: {remaining} сек.\n💰 Награда: {job['reward']}₽\n\n<i>Напиши /check чтобы проверить готовность</i>"
    
    await edit_msg(callback.message, 
        f"💼 <b>ПОДРАБОТКИ</b>\n\nЗаработай пока ждёшь покупателей!\nВыбери работу:{active_job}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("start_job_"))
async def start_job(callback: CallbackQuery):
    user_id = callback.from_user.id
    job_idx = int(callback.data.split("_")[2])
    job = JOBS[job_idx]
    
    # Проверяем нет ли активной работы
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        job_data = side_jobs[user_id]
        elapsed = int(time_module.time() - job_data["start_time"])
        if elapsed < job_data["duration"]:
            remaining = job_data["duration"] - elapsed
            return await callback.answer(f"Уже работаешь! Осталось {remaining} сек.")
    
    side_jobs[user_id] = {
        "type": job_idx,
        "start_time": time_module.time(),
        "reward": job["reward"],
        "duration": job["duration"],
        "done": False
    }
    
    await send_msg(user_id, 
        f"💼 <b>ПРИСТУПИЛ К РАБОТЕ!</b>\n\n"
        f"{job['emoji']} {job['name']}\n"
        f"⏱ Длительность: {job['duration']} сек.\n"
        f"💰 Награда: {job['reward']}₽\n\n"
        f"<i>Напиши /check через {job['duration']} сек. чтобы получить деньги!\n"
        f"Можешь продолжать играть — работа идёт фоном.</i>")
    await callback.answer("Приступил к работе!")

@dp.message(Command('check'))
async def check_job(message: types.Message):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    
    if user_id not in side_jobs or side_jobs[user_id].get("done", True):
        return await send_msg(user_id, "💼 У тебя нет активной работы.\nЗайди в меню и выбери подработку!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 ПОДРАБОТКИ", callback_data="action_job")],
        ]))
    
    job_data = side_jobs[user_id]
    elapsed = int(time_module.time() - job_data["start_time"])
    
    if elapsed >= job_data["duration"] and not job_data["done"]:
        # Работа завершена!
        job_data["done"] = True
        reward = job_data["reward"]
        if user_id in players:
            players[user_id]["balance"] += reward
            players[user_id]["stat_earned_today"] += reward
        
        job = JOBS[job_data["type"]]
        await send_msg(user_id, 
            f"✅ <b>РАБОТА ЗАВЕРШЕНА!</b>\n\n"
            f"{job['emoji']} {job['name']}\n"
            f"💰 Заработано: {reward}₽\n"
            f"💼 Баланс: {players[user_id]['balance']}₽\n\n"
            f"<i>Можешь взять новую подработку или продолжить торговать!</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💼 ЕЩЁ ЗАРАБОТОК", callback_data="action_job")],
                [InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")],
            ]))
    else:
        remaining = job_data["duration"] - elapsed
        job = JOBS[job_data["type"]]
        await send_msg(user_id, 
            f"⏳ <b>РАБОТАЕМ...</b>\n\n"
            f"{job['emoji']} {job['name']}\n"
            f"Осталось: {remaining} сек.\n"
            f"💰 Награда: {job['reward']}₽\n\n"
            f"<i>Напиши /check позже чтобы получить деньги</i>")

@dp.message(Command('job'))
async def job_cmd(message: types.Message):
    user_id = message.from_user.id
    await del_user_msgs(user_id)
    await show_jobs_from_cmd(message)

async def show_jobs_from_cmd(message):
    user_id = message.from_user.id
    kb = []
    for job in JOBS:
        kb.append([InlineKeyboardButton(
            text=f"{job['emoji']} {job['name']} — {job['reward']}₽ ({job['duration']} сек)",
            callback_data=f"start_job_{JOBS.index(job)}"
        )])
    kb.append([InlineKeyboardButton(text="🏠 МЕНЮ", callback_data="action_back")])
    
    active_job = ""
    if user_id in side_jobs and not side_jobs[user_id].get("done", True):
        job_data = side_jobs[user_id]
        elapsed = int(time_module.time() - job_data["start_time"])
        remaining = max(0, job_data["duration"] - elapsed)
        job = JOBS[job_data["type"]]
        active_job = f"\n\n⏳ <b>Работаю:</b> {job['emoji']} {job['name']}\nОсталось: {remaining} сек.\nНапиши /check чтобы проверить"
    
    await send_msg(user_id, f"💼 <b>ПОДРАБОТКИ</b>\n\nЗаработай пока ждёшь!\nВыбери:{active_job}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())