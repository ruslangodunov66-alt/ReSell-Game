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
API_TOKEN = '8747685010:AAH8bN3x0fihSvUzVitijYQLHXeHFhIV5w4'  # ← ЗАМЕНИ
CHANNEL_LINK = '@vintagedrop61'
CHANNEL_NAME = 'ReSell👾'
BOT_USERNAME = 'R-Game'  # ← ЗАМЕНИ БЕЗ @
DEEPSEEK_API_KEY = "sk-9515baacbf9b44bfbf45caadf97e5012"  # ← ЗАМЕНИ

# DeepSeek клиент
client_openai = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==================== ФАЙЛЫ ДАННЫХ ====================
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

# ==================== ТОВАРЫ ====================
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

BUYER_NAMES = [
    "Вася", "Петя", "Колян", "Димон", "Антоха", "Серёга", "Макс",
    "Лёха", "Вован", "Гоша", "Мишаня", "Тёмыч", "Даня", "Егор",
    "Никита", "Рустам", "Жека", "Илюха", "Стас", "Артём"
]

BUYER_HAGGLE_MESSAGES = [
    "👤 {name}: Слушай, а за {offer} отдашь? У меня сейчас столько есть.",
    "👤 {name}: Братан, {offer} — и я прямо сейчас забираю. По рукам?",
    "👤 {name}: А чё так дорого? Давай {offer}, я видел дешевле.",
    "👤 {name}: Ну {offer} — последняя цена. Или я ушёл.",
    "👤 {name}: У меня в закладках такой же за {offer} висит. Продашь?",
    "👤 {name}: {offer} и ни копейкой больше. Берёшь?",
    "👤 {name}: Слушай, мне очень надо, но денег {offer} всего. Идёт?",
]

BUYER_ACCEPT_MESSAGES = [
    "👤 {name}: 👌 Договорились! Забираю.",
    "👤 {name}: ✅ По рукам! Сейчас переведу.",
    "👤 {name}: 🔥 Отлично! Давай встретимся сегодня.",
    "👤 {name}: 💯 Беру! Скидывай данные для перевода.",
]

BUYER_DECLINE_MESSAGES = [
    "👤 {name}: 😕 Дороговато. Пойду ещё поищу.",
    "👤 {name}: ❌ Не, не готов столько отдать. Удачи.",
    "👤 {name}: 🤷 Ладно, подумаю. Пока.",
    "👤 {name}: 👋 Слишком дорого. Бывай.",
]

BUYER_NOT_INTERESTED = [
    "👤 {name}: Не, {cat} сейчас не в тему. Давай что-нибудь другое.",
    "👤 {name}: {cat}? Уже купил вчера. Нужны кроссы.",
    "👤 {name}: Слушай, а {cat} есть что-нибудь ещё? Это не моё.",
    "👤 {name}: {cat} не ношу. Может, куртки есть?",
]

MARKET_EVENTS = [
    {"text": "📰 Хайп на винтажные джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — спрос на куртки вырос!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Все хотят кроссовки как у Pharaoh.", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы падают.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито комиссия 15% — все осторожны.", "cat": None, "mult": 0.8},
    {"text": "📰 Ретро-аксессуары в тренде!", "cat": "🎒 Аксессуары", "mult": 1.6},
    {"text": "📰 Холода задерживаются — куртки в цене.", "cat": "🧥 Куртки", "mult": 1.3},
    {"text": "📰 Скоро школа — худи дорожают.", "cat": "👕 Худи", "mult": 1.35},
    {"text": "📰 Кроссовки — рынок переполнен.", "cat": "👟 Кроссы", "mult": 0.65},
    {"text": "📰 Блогер засветился в Stüssy!", "cat": "🎒 Аксессуары", "mult": 1.5},
    {"text": "📰 Блокировки Авито — конкуренция ниже.", "cat": None, "mult": 1.2},
    {"text": "📰 Эконом-режим — ищут дешёвое.", "cat": None, "mult": 0.7},
]

# ==================== НЕЙРОКЛИЕНТЫ ====================
CLIENT_TYPES = {
    "angry": {
        "name": "злой", "mood_emoji": "😡",
        "system_prompt": "Ты — злой покупатель. Грубишь, торгуешься жёстко (скидка 30-50%), уходишь если не уступают. Коротко, 1-2 предложения.",
        "discount_range": (0.5, 0.7), "patience": 2
    },
    "kind": {
        "name": "добрый", "mood_emoji": "😊",
        "system_prompt": "Ты — добрый покупатель. Вежлив, просишь скидку 10-20%, хвалишь товар. Коротко, 1-2 предложения.",
        "discount_range": (0.8, 0.9), "patience": 5
    },
    "sly": {
        "name": "хитрый", "mood_emoji": "😏",
        "system_prompt": "Ты — хитрый перекупщик. Аргументируешь цену, блефуешь, сбиваешь 20-40%. Коротко, как в чате Авито.",
        "discount_range": (0.6, 0.8), "patience": 4
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
    {"id": "seller_50", "name": "🏪 Магазин", "target": 50, "reward": 20},
    {"id": "profit_5000", "name": "💰 Навар", "target": 5000, "reward": 5},
    {"id": "profit_50000", "name": "💸 Богач", "target": 50000, "reward": 15},
    {"id": "angry_win", "name": "😡 Укротитель", "target": 1, "reward": 10},
    {"id": "haggle_master", "name": "🎯 Мастер торга", "target": 1, "reward": 10},
]

# ==================== БОТ ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()

# ==================== ГЛОБАЛЬНЫЕ ХРАНИЛИЩА ====================
players = {}
referral_data = defaultdict(lambda: {"invited": [], "bonus_claimed": False})
rep_data = {}
active_chats = {}

# ==================== ЗАГРУЗКА ДАННЫХ ====================
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
            "max_balance": 0, "scam_survived": 0, "vip_purchases": 0,
            "angry_deals": 0, "haggle_wins": 0, "achievements": [], "rep_history": []
        }
        save_json(REPUTATION_FILE, rep_data)
    return rep_data[uid]

def get_rep_level(score):
    for t in sorted(REPUTATION_LEVELS.keys(), reverse=True):
        if score >= t:
            return REPUTATION_LEVELS[t]
    return REPUTATION_LEVELS[-100]

def add_rep(user_id, amount, reason=""):
    user = get_user_rep(user_id)
    old_score = user["score"]
    user["score"] = max(-100, min(100, user["score"] + amount))
    user["rep_history"].append({"change": amount, "reason": reason, "total": user["score"]})
    if len(user["rep_history"]) > 20:
        user["rep_history"] = user["rep_history"][-20:]
    save_json(REPUTATION_FILE, rep_data)
    return user["score"]

def get_rep_multiplier(score):
    if score >= 75: return {"supplier_discount": 0.85, "scam_reduce": 0.2, "haggle_bonus": 0.25}
    elif score >= 50: return {"supplier_discount": 0.90, "scam_reduce": 0.4, "haggle_bonus": 0.15}
    elif score >= 25: return {"supplier_discount": 0.95, "scam_reduce": 0.6, "haggle_bonus": 0.05}
    elif score >= 0: return {"supplier_discount": 1.0, "scam_reduce": 0.8, "haggle_bonus": 0.0}
    elif score >= -10: return {"supplier_discount": 1.1, "scam_reduce": 1.0, "haggle_bonus": -0.05}
    elif score >= -50: return {"supplier_discount": 1.25, "scam_reduce": 1.2, "haggle_bonus": -0.15}
    else: return {"supplier_discount": 1.5, "scam_reduce": 1.5, "haggle_bonus": -0.3}

def check_achievements(user_id, player_data=None):
    user = get_user_rep(user_id)
    if player_data:
        user["total_sales"] = player_data.get("items_sold", 0)
        user["total_profit"] = player_data.get("total_earned", 0)
        user["max_balance"] = max(user["max_balance"], player_data.get("balance", 0))
        user["scam_survived"] = player_data.get("scam_times", 0)
    new_ach = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in user["achievements"]:
            continue
        earned = False
        tid = ach["id"]
        if tid == "first_sale" and user["total_sales"] >= 1: earned = True
        elif tid == "seller_10" and user["total_sales"] >= 10: earned = True
        elif tid == "seller_50" and user["total_sales"] >= 50: earned = True
        elif tid == "profit_5000" and user["total_profit"] >= 5000: earned = True
        elif tid == "profit_50000" and user["total_profit"] >= 50000: earned = True
        elif tid == "angry_win" and user["angry_deals"] >= 1: earned = True
        elif tid == "haggle_master" and user["haggle_wins"] >= 1: earned = True
        if earned:
            user["achievements"].append(ach["id"])
            add_rep(user_id, ach["reward"], f"Достижение: {ach['name']}")
            new_ach.append(ach)
    save_json(REPUTATION_FILE, rep_data)
    return new_ach

def format_rep_card(user_id):
    user = get_user_rep(user_id)
    level = get_rep_level(user["score"])
    mult = get_rep_multiplier(user["score"])
    bar_len = 10
    filled = int((user["score"] + 100) / 200 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    lines = [
        f"🏆 <b>РЕПУТАЦИЯ: {level['name']}</b>",
        f"📊 Очки: {user['score']}/100  [{bar}]",
        f"📦 Продаж: {user['total_sales']} | 💰 Прибыль: {user['total_profit']}₽",
        f"🏅 Достижений: {len(user['achievements'])}/{len(ACHIEVEMENTS)}",
    ]
    return "\n".join(lines)

# ==================== НЕЙРОКЛИЕНТЫ ====================
def neuro_first_message(client_type, item_name, price, offer):
    msgs = {
        "angry": [
            f"Чё за {price}₽ за {item_name}? Давай {offer}₽ или я пошёл.",
            f"{price}₽ — грабёж! {offer}₽ максимум. Берёшь?",
        ],
        "kind": [
            f"Здравствуйте! {item_name} нравится, но {price}₽ дорого. Может {offer}₽?",
            f"Добрый день! Бюджет {offer}₽ на {item_name}. Договоримся?",
        ],
        "sly": [
            f"Бро, {item_name} за {offer}₽ на другом акке. Отдашь за {offer}₽?",
            f"Рынок {item_name} — {offer}₽. Давай по рынку?",
        ]
    }
    return random.choice(msgs.get(client_type, msgs["kind"]))

def start_neuro_chat(user_id, item_name, item_price, client_type=None):
    if client_type is None:
        client_type = random.choice(list(CLIENT_TYPES.keys()))
    client = CLIENT_TYPES[client_type]
    rep_mult = get_rep_multiplier(get_user_rep(user_id)["score"])
    if rep_mult["haggle_bonus"] > 0.1 and client_type == "angry" and random.random() < rep_mult["haggle_bonus"]:
        client_type = "sly"; client = CLIENT_TYPES[client_type]
    if rep_mult["haggle_bonus"] < 0 and client_type == "kind" and random.random() < abs(rep_mult["haggle_bonus"]):
        client_type = "angry"; client = CLIENT_TYPES[client_type]
    discount = random.uniform(*client["discount_range"]) + rep_mult["haggle_bonus"]
    discount = max(0.3, min(0.95, discount))
    offer = int(item_price * discount)
    offer = (offer // 100) * 100 + 99
    if offer < 100: offer = item_price // 2
    first_msg = neuro_first_message(client_type, item_name, item_price, offer)
    active_chats[user_id] = {
        "client_type": client_type, "item": item_name, "price": item_price,
        "offer": offer, "history": [
            {"role": "system", "content": client["system_prompt"]},
            {"role": "assistant", "content": first_msg}
        ], "round": 1, "max_rounds": client["patience"], "finished": False
    }
    return {"message": first_msg, "client_type": client_type, "client_name": client["name"],
            "emoji": client["mood_emoji"], "offer": offer, "round": 1, "max_rounds": client["patience"]}

def neuro_chat(user_id, user_message):
    if user_id not in active_chats or active_chats[user_id]["finished"]:
        return {"error": "Нет диалога"}
    chat = active_chats[user_id]; client = CLIENT_TYPES[chat["client_type"]]
    chat["history"].append({"role": "user", "content": user_message}); chat["round"] += 1
    if chat["round"] > chat["max_rounds"]:
        chat["finished"] = True
        msgs = {"angry": "Всё, я пошёл!", "kind": "Ладно, подумаю. Спасибо!", "sly": "Хорошо, удачи."}
        return {"finished": True, "result": "lost", "message": msgs.get(chat["client_type"], "Пока."), "emoji": "👋"}
    try:
        resp = client_openai.chat.completions.create(model="deepseek-chat", messages=chat["history"], temperature=0.9, max_tokens=150)
        ai_msg = resp.choices[0].message.content
    except:
        ai_msg = f"Моё предложение {chat['offer']}₽. Берёшь?"
    chat["history"].append({"role": "assistant", "content": ai_msg})
    finished, result = False, None
    ml = ai_msg.lower()
    agree = ["беру", "договорились", "по рукам", "забираю", "согласен"]
    for w in agree:
        if w in ml: finished, result = True, "sold"; break
    if not finished and ("нет" in ml or "ушёл" in ml or "пока" in ml):
        finished, result = True, "lost"
    if finished: chat["finished"] = True
    return {"finished": finished, "result": result, "message": ai_msg, "round": chat["round"], "emoji": client["mood_emoji"]}

def get_chat_status(user_id):
    if user_id not in active_chats or active_chats[user_id]["finished"]: return None
    c = active_chats[user_id]
    return {"client_type": c["client_type"], "item": c["item"], "price": c["price"],
            "current_offer": c["offer"], "round": c["round"], "max_rounds": c["max_rounds"],
            "emoji": CLIENT_TYPES[c["client_type"]]["mood_emoji"]}

def end_chat(user_id):
    if user_id in active_chats: del active_chats[user_id]

# ==================== ИГРА ====================
def get_player(user_id):
    if user_id not in players:
        rep = get_user_rep(user_id)
        rep_mult = get_rep_multiplier(rep["score"])
        players[user_id] = {
            "balance": 5000, "reputation": max(0, rep["score"]),
            "inventory": [], "day": 1, "total_earned": 0, "total_spent": 0,
            "items_sold": rep["total_sales"], "scam_times": rep["scam_survived"],
            "market_demand": {cat: 1.0 for cat in CATEGORIES}, "current_event": None,
            "stat_earned_today": 0, "stat_sold_today": 0, "rep_mult": rep_mult,
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

def format_inventory(inv):
    if not inv: return "📦 Инвентарь пуст."
    return "📦 <b>ИНВЕНТАРЬ:</b>\n" + "\n".join(
        f"{i}. {it['name']} | Закуп: {it['buy_price']}₽ | ~{it['market_price']}₽"
        for i, it in enumerate(inv, 1)
    )

def get_main_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУП", callback_data="action_buy"),
         InlineKeyboardButton(text="📦 ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="🧠 НЕЙРОКЛИЕНТ", callback_data="action_neuro"),
         InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats")],
        [InlineKeyboardButton(text="🏆 РЕПУТАЦИЯ", callback_data="action_rep"),
         InlineKeyboardButton(text="🔗 РЕФЕРАЛЫ", callback_data="action_ref")],
        [InlineKeyboardButton(text="⏩ СЛЕД. ДЕНЬ", callback_data="action_nextday"),
         InlineKeyboardButton(text="🏁 ЗАВЕРШИТЬ", callback_data="action_end")],
    ])
    return kb

async def check_game_over(message, p):
    if p["balance"] >= 50000:
        await message.answer(f"🏆 <b>ПОБЕДА!</b> 50 000₽!\nРеальные продажи → {CHANNEL_LINK}", parse_mode="HTML")
    elif p["balance"] <= 0:
        await message.answer(f"💀 <b>БАНКРОТ</b>\nВ реальности → {CHANNEL_LINK}\n/play — ещё раз", parse_mode="HTML")

# ==================== КОМАНДЫ ====================
@dp.message(Command('start'))
async def start_cmd(message: types.Message):
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
            try: await bot.send_message(int(referrer_id), f"🎉 Новый реферал! +500₽\n👥 Всего: {len(referral_data[referrer_id]['invited'])}", parse_mode="HTML")
            except: pass
            await message.answer("👋 Привет! Ты по реферальной ссылке.\n/play — играть | /ref — ссылка | /chat — нейроклиент", parse_mode="HTML")
            return
    await message.answer(f"🎮 <b>ReSell Tycoon</b>\n💰 5 000₽ → 🎯 50 000₽\n\n/play | /ref | /rep | /chat | /rating", parse_mode="HTML")

@dp.message(Command('play'))
async def play_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
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
    await message.answer(f"🌟 <b>ДЕНЬ 1</b>\nБаланс: 5000₽{vip_txt}{et}\n\nВыбери:", parse_mode="HTML", reply_markup=get_main_keyboard())

@dp.message(Command('ref'))
async def ref_cmd(message: types.Message):
    user_id = message.from_user.id
    link = get_ref_link(user_id)
    count = len(referral_data[str(user_id)]["invited"])
    vip_user = is_vip(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 РЕЙТИНГ", callback_data="show_rating")]
    ])
    vip_txt = "\n👑 Ты в ТОП-3! VIP открыт!" if vip_user else ""
    await message.answer(f"🔗 <b>ТВОЯ ССЫЛКА:</b>\n<code>{link}</code>\n\n👥 Приглашено: {count}\n💰 Бонус: {count*500}₽{vip_txt}", parse_mode="HTML", reply_markup=kb)

@dp.message(Command('rating'))
async def rating_cmd(message: types.Message):
    top = get_top_referrers(10)
    if not top: return await message.answer("🏆 Рейтинг пуст.")
    lines = ["🏆 <b>ТОП-10:</b>\n"]
    medals = ["🥇","🥈","🥉"] + ["▫️"]*7
    for i, (uid, count) in enumerate(top):
        lines.append(f"{medals[i]} ID:{uid} — <b>{count}</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")

@dp.message(Command('rep'))
async def rep_cmd(message: types.Message):
    user_id = message.from_user.id
    p = players.get(user_id)
    pd = {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]} if p else None
    new_ach = check_achievements(user_id, pd)
    card = format_rep_card(user_id)
    if new_ach:
        card += "\n\n🎉 <b>НОВЫЕ!</b>\n" + "\n".join(f"{a['name']}" for a in new_ach)
    await message.answer(card, parse_mode="HTML")

@dp.message(Command('chat'))
async def neuro_start_cmd(message: types.Message):
    user_id = message.from_user.id
    p = get_player(user_id)
    if not p["inventory"]: return await message.answer("📦 Нет товаров. /play")
    item = random.choice(p["inventory"])
    data = start_neuro_chat(user_id, item["name"], item["market_price"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Предложить", callback_data="neuro_offer"),
         InlineKeyboardButton(text="✅ Согласиться", callback_data="neuro_accept")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="neuro_decline"),
         InlineKeyboardButton(text="📊 Инфо", callback_data="neuro_info")],
    ])
    await message.answer(
        f"🧠 <b>НЕЙРОКЛИЕНТ</b>\n📦 {item['name']}\n💰 Цена: {item['market_price']}₽\n"
        f"Тип: {data['client_name'].upper()} {data['emoji']}\n\n"
        f"{data['emoji']} <b>Клиент:</b> {data['message']}\n\n"
        f"<i>Раунд {data['round']}/{data['max_rounds']}</i>\nПиши ответ или жми кнопку:",
        parse_mode="HTML", reply_markup=kb
    )

@dp.message(StateFilter(GameState.playing))
async def neuro_text_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in active_chats or active_chats[user_id]["finished"]: return
    resp = neuro_chat(user_id, message.text)
    if "error" in resp: return await message.answer("Диалог завершён. /chat")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Предложить", callback_data="neuro_offer"),
         InlineKeyboardButton(text="✅ Согласиться", callback_data="neuro_accept")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="neuro_decline")],
    ])
    if resp["finished"]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Новый клиент", callback_data="new_neuro")],
        ])
    txt = f"{resp['emoji']} <b>Клиент:</b> {resp['message']}"
    if resp["finished"]: txt += f"\n\n⚠️ Диалог завершён! {'🎉 Готов купить!' if resp['result'] == 'sold' else '👋 Ушёл.'}"
    await message.answer(txt, parse_mode="HTML", reply_markup=kb)

# ==================== CALLBACK-ОБРАБОТЧИКИ ====================
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
    await callback.message.edit_text(f"🏭 <b>ПОСТАВЩИКИ:</b>{vip_txt}\nРейтинг ↑ = надёжнее, но дороже.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
    await callback.message.edit_text(f"{sup['emoji']} <b>{sup['name']}</b>\n⭐{sup['rating']}/10 | ⚠️Кид:{sup['scam_chance']}%\nВыбери:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

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
        await callback.message.edit_text(f"💀 <b>КИНУЛИ!</b>\n{sup['name']} пропал.\n-{price}₽ | Баланс: {p['balance']}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]]))
        return await check_game_over(callback.message, p)
    p["balance"] -= price; p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    p["inventory"].append({"name": f"{item['cat']} {item['name']}", "cat": item["cat"], "buy_price": price, "market_price": get_market_price(item["base_price"], demand), "base_price": item["base_price"]})
    if sup["rating"] >= 8: add_rep(user_id, 1, "Надёжный поставщик")
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(f"✅ <b>КУПЛЕНО!</b>\n📦 {item['cat']} {item['name']}\n💰 Закуп: {price}₽\n💼 Баланс: {p['balance']}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё", callback_data=f"supplier_{sup_idx}")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_inventory", StateFilter(GameState.playing))
async def show_inventory(callback: CallbackQuery):
    p = get_player(callback.from_user.id)
    if not p["inventory"]:
        return await callback.message.edit_text("📦 Пусто.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏭 Закупиться", callback_data="action_buy")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]
        ]))
    kb = []
    for i, it in enumerate(p["inventory"]):
        kb.append([InlineKeyboardButton(text=f"{it['name']} | Закуп:{it['buy_price']}₽ | ~{it['market_price']}₽", callback_data=f"sell_{i}")])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")])
    await callback.message.edit_text(format_inventory(p["inventory"]) + "\n\nВыбери для продажи:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("sell_"), StateFilter(GameState.playing))
async def try_sell(callback: CallbackQuery, state: FSMContext):
    item_idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Нет товара")
    item = p["inventory"][item_idx]
    buyer = random.choice(BUYER_NAMES)
    demand = p["market_demand"].get(item["cat"], 1.0)
    if random.random() > min(0.9, demand * 0.6):
        msg = random.choice(BUYER_NOT_INTERESTED).format(name=buyer, cat=item["cat"])
        return await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Инвентарь", callback_data="action_inventory")],
        ]))
    offer = int(item["market_price"] * random.uniform(0.7, 1.1))
    await state.update_data(selling_item_idx=item_idx, buyer_offer=offer, buyer_name=buyer)
    msg = random.choice(BUYER_HAGGLE_MESSAGES).format(name=buyer, offer=offer)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="accept_offer"),
         InlineKeyboardButton(text="📈 Торг +10%", callback_data="haggle_up")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="decline_offer")],
    ])
    await callback.message.edit_text(f"👤 <b>{buyer}</b>\n📦 {item['name']}\n💰 Закуп: {item['buy_price']}₽ | ~{item['market_price']}₽\n\n{msg}", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "accept_offer", StateFilter(GameState.playing))
async def accept_offer(callback: CallbackQuery, state: FSMContext):
    await complete_sale(callback, state, 0)

@dp.callback_query(F.data == "haggle_up", StateFilter(GameState.playing))
async def haggle_up(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    offer = data.get("buyer_offer", 0)
    new_offer = int(offer * 1.1)
    user_id = callback.from_user.id
    p = get_player(user_id)
    chance = 0.3 + (p["reputation"] / 100) * 0.4 + p["rep_mult"]["haggle_bonus"]
    if random.random() < chance:
        await state.update_data(buyer_offer=new_offer)
        await complete_sale(callback, state, new_offer - offer)
    else:
        await callback.message.edit_text("👤 Покупатель: ❌ Не, дорого. Ушёл.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Инвентарь", callback_data="action_inventory")],
        ]))

@dp.callback_query(F.data == "decline_offer", StateFilter(GameState.playing))
async def decline_offer(callback: CallbackQuery):
    await callback.message.edit_text("👤 Покупатель: 👋 Бывай.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Инвентарь", callback_data="action_inventory")],
    ]))

async def complete_sale(callback, state, haggle_bonus):
    data = await state.get_data()
    item_idx = data.get("selling_item_idx", 0)
    buyer = data.get("buyer_name", "Покупатель")
    final = data.get("buyer_offer", 0)
    user_id = callback.from_user.id
    p = get_player(user_id)
    if item_idx >= len(p["inventory"]): return await callback.answer("Ошибка")
    item = p["inventory"].pop(item_idx)
    p["balance"] += final
    profit = final - item["buy_price"]
    p["total_earned"] += profit; p["items_sold"] += 1
    p["stat_earned_today"] += profit; p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + random.randint(1, 5))
    add_rep(user_id, random.randint(1, 4), f"Продажа: {item['name']}")
    if haggle_bonus > 0:
        add_rep(user_id, 3, "Успешный торг")
        get_user_rep(user_id)["haggle_wins"] += 1
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"], "scam_times": p["scam_times"]})
    save_json(REPUTATION_FILE, rep_data)
    msg = random.choice(BUYER_ACCEPT_MESSAGES).format(name=buyer)
    bonus_txt = f"\n🔥 +{haggle_bonus}₽ торгом!" if haggle_bonus else ""
    await callback.message.edit_text(f"{msg}\n\n📦 {item['name']}\n💰 {final}₽ | 💵 +{profit}₽{bonus_txt}\n💼 Баланс: {p['balance']}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Инвентарь", callback_data="action_inventory")],
    ]))
    await check_game_over(callback.message, p)

@dp.callback_query(F.data == "action_neuro", StateFilter(GameState.playing))
async def neuro_btn(callback: CallbackQuery):
    await neuro_start_cmd(callback.message)

@dp.callback_query(F.data == "neuro_offer", StateFilter(GameState.playing))
async def neuro_offer_btn(callback: CallbackQuery):
    s = get_chat_status(callback.from_user.id)
    if not s: return await callback.answer("Нет диалога")
    await callback.message.answer(f"Цена: {s['price']}₽ | Предложение: {s['current_offer']}₽\nНапиши встречную цену (число):")
    await callback.answer()

@dp.callback_query(F.data == "neuro_accept", StateFilter(GameState.playing))
async def neuro_accept_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    s = get_chat_status(user_id)
    if not s: return await callback.answer("Нет диалога")
    neuro_chat(user_id, f"Согласен на {s['current_offer']}₽")
    await neuro_complete_sale(callback, s)

@dp.callback_query(F.data == "neuro_decline", StateFilter(GameState.playing))
async def neuro_decline_btn(callback: CallbackQuery):
    user_id = callback.from_user.id
    neuro_chat(user_id, "Нет, не устраивает.")
    end_chat(user_id)
    await callback.message.edit_text("❌ Отказано. /chat — новый клиент")

@dp.callback_query(F.data == "neuro_info", StateFilter(GameState.playing))
async def neuro_info_btn(callback: CallbackQuery):
    s = get_chat_status(callback.from_user.id)
    if not s: return await callback.answer("Нет диалога")
    cl = CLIENT_TYPES[s["client_type"]]
    await callback.answer(f"{cl['name'].upper()} {cl['mood_emoji']} | Раунд {s['round']}/{s['max_rounds']}", show_alert=True)

@dp.callback_query(F.data == "new_neuro")
async def new_neuro_btn(callback: CallbackQuery):
    await neuro_start_cmd(callback.message)

async def neuro_complete_sale(callback, status):
    user_id = callback.from_user.id
    p = get_player(user_id)
    for i, item in enumerate(p["inventory"]):
        if item["name"] == status["item"]:
            sold = p["inventory"].pop(i)
            profit = status["current_offer"] - sold["buy_price"]
            p["balance"] += status["current_offer"]
            p["total_earned"] += profit; p["items_sold"] += 1
            p["reputation"] = min(100, p["reputation"] + 5)
            add_rep(user_id, random.randint(2, 5), f"Продажа нейроклиенту")
            if status["client_type"] == "angry":
                get_user_rep(user_id)["angry_deals"] += 1
            if status["current_offer"] > status["price"] * 0.9:
                get_user_rep(user_id)["haggle_wins"] += 1
            check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
            save_json(REPUTATION_FILE, rep_data)
            end_chat(user_id)
            await callback.message.answer(f"🎉 <b>ПРОДАНО!</b>\n📦 {sold['name']}\n💰 {status['current_offer']}₽ | 💵 +{profit}₽\n💼 Баланс: {p['balance']}₽", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Новый клиент", callback_data="new_neuro")],
            ]))
            return
    await callback.message.answer("Товар не найден."); end_chat(user_id)

@dp.callback_query(F.data == "action_stats", StateFilter(GameState.playing))
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    dl = [f"{'📈' if m>1 else '📉' if m<1 else '➡️'} {c}: x{m:.1f}" for c, m in p["market_demand"].items()]
    ref_n = len(referral_data[str(user_id)]["invited"])
    vip = "👑 ДА" if is_vip(user_id) else "❌ Нет"
    await callback.message.edit_text(f"💰 Баланс: {p['balance']}₽\n⭐ Реп: {p['reputation']}/100\n📅 День: {p['day']}\n📦 Товаров: {len(p['inventory'])}\n👥 Рефералы: {ref_n}\n👑 VIP: {vip}\n\n📊 <b>СПРОС:</b>\n"+"\n".join(dl), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Меню", callback_data="action_back")]
    ]))

@dp.callback_query(F.data == "action_rep")
async def rep_btn(callback: CallbackQuery):
    await rep_cmd(callback.message)

@dp.callback_query(F.data == "action_ref")
async def ref_btn(callback: CallbackQuery):
    await ref_cmd(callback.message)

@dp.callback_query(F.data == "show_rating")
async def show_rating_btn(callback: CallbackQuery):
    await rating_cmd(callback.message)

@dp.callback_query(F.data == "action_nextday", StateFilter(GameState.playing))
async def next_day(callback: CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    summary = f"🌙 <b>ИТОГИ ДНЯ {p['day']}</b>\n💰 Заработано: {p['stat_earned_today']}₽\n📋 Продано: {p['stat_sold_today']} шт.\n💼 Баланс: {p['balance']}₽"
    p["day"] += 1; p["stat_earned_today"] = 0; p["stat_sold_today"] = 0
    for c in CATEGORIES: p["market_demand"][c] = max(0.3, min(3.0, p["market_demand"][c] * random.uniform(0.85, 1.15)))
    event = generate_daily_event(); p["current_event"] = event
    if event: apply_market_event(p, event)
    et = f"\n\n{event['text']}" if event else ""
    if p["inventory"] and random.random() < 0.2:
        for it in p["inventory"]: it["market_price"] = int(it["market_price"] * random.uniform(0.7, 0.95))
        et += "\n⚠️ Товары залежались — потеря в цене."
    vip_txt = "\n👑 VIP" if is_vip(user_id) else ""
    check_achievements(user_id, {"items_sold": p["items_sold"], "total_earned": p["total_earned"], "balance": p["balance"]})
    save_json(REPUTATION_FILE, rep_data)
    await callback.message.edit_text(f"{summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{vip_txt}{et}\n\nВыбери:", parse_mode="HTML", reply_markup=get_main_keyboard())

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
    await callback.message.edit_text(f"{result}\n💰 Баланс: {p['balance']}₽\n📦 Продаж: {p['items_sold']}\n\nРеальные продажи → {CHANNEL_LINK}\n/play — ещё раз", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё раз", callback_data="restart_game")],
    ]))

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
    await callback.message.edit_text(f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{vip_txt}{et}\n\nДействие:", parse_mode="HTML", reply_markup=get_main_keyboard())

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())