# bot.py — ReSell Tycoon (aiogram 3.x)
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from settings import BOT_TOKEN

# ==================== ДАННЫЕ ====================

SUPPLIERS = [
    {"name": "🏭 MegaStock", "rating": 9, "price_mult": 1.4, "scam_chance": 0},
    {"name": "👕 OldGarage", "rating": 7, "price_mult": 1.15, "scam_chance": 10},
    {"name": "🎒 Vintager", "rating": 5, "price_mult": 0.85, "scam_chance": 25},
    {"name": "💸 DumpPrice", "rating": 3, "price_mult": 0.55, "scam_chance": 50},
    {"name": "🎲 LuckyBag", "rating": 1, "price_mult": 0.3, "scam_chance": 75},
]

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
]

CATEGORIES = ["👖 Джинсы", "👕 Худи", "🧥 Куртки", "👟 Кроссы", "🎒 Аксессуары"]

BUYER_NAMES = [
    "Вася", "Петя", "Колян", "Димон", "Антоха", "Серёга", "Макс",
    "Лёха", "Вован", "Гоша", "Мишаня", "Тёмыч", "Даня", "Егор"
]

MARKET_EVENTS = [
    {"text": "📰 Хайп на винтажные джинсы!", "cat": "👖 Джинсы", "mult": 1.5},
    {"text": "📰 Дожди — спрос на куртки вырос!", "cat": "🧥 Куртки", "mult": 1.4},
    {"text": "📰 Все хотят кроссовки как у блогера.", "cat": "👟 Кроссы", "mult": 1.5},
    {"text": "📰 Лето близко — джинсы и худи падают.", "cat": "👖 Джинсы", "mult": 0.6},
    {"text": "📰 Авито ввело комиссию 15% — рынок просел.", "cat": None, "mult": 0.8},
    {"text": "📰 Ретро-аксессуары на пике!", "cat": "🎒 Аксессуары", "mult": 1.6},
    {"text": "📰 Холода задерживаются — куртки в цене.", "cat": "🧥 Куртки", "mult": 1.3},
    {"text": "📰 Школьный сезон — худи нужны всем.", "cat": "👕 Худи", "mult": 1.35},
    {"text": "📰 Кроссовки — рынок переполнен.", "cat": "👟 Кроссы", "mult": 0.65},
    {"text": "📰 Блокировки на Авито — конкуренция ниже.", "cat": None, "mult": 1.2},
]

# ==================== ХРАНИЛИЩЕ В ПАМЯТИ ====================
players = {}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_player(user_id):
    if user_id not in players:
        players[user_id] = {
            "balance": 5000,
            "reputation": 20,
            "inventory": [],
            "day": 1,
            "total_earned": 0,
            "total_spent": 0,
            "items_sold": 0,
            "scam_times": 0,
            "market_demand": {cat: 1.0 for cat in CATEGORIES},
            "current_event": None,
            "stat_earned_today": 0,
            "stat_sold_today": 0,
        }
    return players[user_id]

def get_item_price(item_base_price, supplier):
    return int(item_base_price * supplier["price_mult"])

def get_market_price(item_base_price, demand_mult):
    return int(item_base_price * demand_mult * random.uniform(0.9, 1.3))

def generate_daily_event():
    if random.random() < 0.6:
        return random.choice(MARKET_EVENTS)
    return None

def apply_market_event(player_data, event):
    if event["cat"]:
        player_data["market_demand"][event["cat"]] *= event["mult"]
        player_data["market_demand"][event["cat"]] = max(0.3, min(3.0, player_data["market_demand"][event["cat"]]))
    else:
        for cat in CATEGORIES:
            player_data["market_demand"][cat] *= event["mult"]
            player_data["market_demand"][cat] = max(0.3, min(3.0, player_data["market_demand"][cat]))

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏭 ЗАКУПИТЬСЯ У ПОСТАВЩИКОВ", callback_data="action_buy")],
        [InlineKeyboardButton(text="📦 МОЙ ИНВЕНТАРЬ", callback_data="action_inventory")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="action_stats")],
        [InlineKeyboardButton(text="⏩ СЛЕДУЮЩИЙ ДЕНЬ", callback_data="action_nextday")],
        [InlineKeyboardButton(text="🏆 ЗАВЕРШИТЬ ИГРУ", callback_data="action_end")],
    ])

# ==================== СОСТОЯНИЯ ====================
class GameState(StatesGroup):
    playing = State()
    choosing_supplier = State()
    selling_item = State()

# ==================== БОТ ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== КОМАНДЫ ====================

@dp.message(Command("start"))
async def start_game(message: types.Message):
    await message.answer(
        "🎮 <b>ReSell Tycoon</b> — Симулятор перекупщика\n\n"
        "Ты — товарщик с бюджетом 5 000₽.\n"
        "Цель — раскрутиться до 50 000₽.\n\n"
        "🔹 Закупай товары у поставщиков\n"
        "🔹 Продавай покупателям (приходят сами)\n"
        "🔹 Следи за рыночным спросом\n"
        "🔹 Остерегайся кидал\n\n"
        "Жми /play чтобы начать!",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("play"))
async def new_game(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    players[user_id] = {
        "balance": 5000,
        "reputation": 20,
        "inventory": [],
        "day": 1,
        "total_earned": 0,
        "total_spent": 0,
        "items_sold": 0,
        "scam_times": 0,
        "market_demand": {cat: 1.0 for cat in CATEGORIES},
        "current_event": None,
        "stat_earned_today": 0,
        "stat_sold_today": 0,
    }
    p = players[user_id]
    event = generate_daily_event()
    p["current_event"] = event
    if event:
        apply_market_event(p, event)

    await state.set_state(GameState.playing)

    event_text = f"\n\n{event['text']}" if event else ""
    await message.answer(
        f"🌟 <b>ДЕНЬ {p['day']}</b>\n"
        f"Стартовый баланс: {p['balance']}₽{event_text}\n\n"
        f"Выбери действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

# ==================== ГЛАВНОЕ МЕНЮ ====================

@dp.callback_query(F.data == "action_buy")
async def show_suppliers(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{s['name']} | Рейтинг {s['rating']}/10 | Кидает {s['scam_chance']}%", 
                              callback_data=f"supplier_{i}")] for i, s in enumerate(SUPPLIERS)
    ] + [[InlineKeyboardButton(text="🔙 НАЗАД", callback_data="action_back")]])

    await callback.message.edit_text(
        "🏭 <b>ПОСТАВЩИКИ:</b>\n\n"
        "Чем выше рейтинг — тем надёжнее, но дороже.\n"
        "Чем ниже рейтинг — тем дешевле, но могут кинуть.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("supplier_"))
async def show_supplier_items(callback: types.CallbackQuery, state: FSMContext):
    supplier_idx = int(callback.data.split("_")[1])
    supplier = SUPPLIERS[supplier_idx]
    await state.update_data(current_supplier_idx=supplier_idx)

    items = random.sample(BASE_ITEMS, min(4, len(BASE_ITEMS)))
    await state.update_data(supplier_items=items)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{item['cat']} {item['name']} — {get_item_price(item['base_price'], supplier)}₽",
            callback_data=f"buyitem_{i}"
        )] for i, item in enumerate(items)
    ] + [
        [InlineKeyboardButton(text="🔄 Обновить товары", callback_data=f"supplier_{supplier_idx}")],
        [InlineKeyboardButton(text="🔙 К поставщикам", callback_data="action_buy")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")],
    ])

    await callback.message.edit_text(
        f"{supplier['name']}\n⭐ Рейтинг: {supplier['rating']}/10\n⚠️ Шанс кидка: {supplier['scam_chance']}%\n\nВыбери товар:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("buyitem_"))
async def buy_item(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item_idx = int(callback.data.split("_")[1])
    supplier_idx = data.get("current_supplier_idx", 0)
    items = data.get("supplier_items", [])

    if item_idx >= len(items):
        await callback.answer("Ошибка загрузки товара.")
        return

    item = items[item_idx]
    supplier = SUPPLIERS[supplier_idx]
    price = get_item_price(item["base_price"], supplier)
    user_id = callback.from_user.id
    p = get_player(user_id)

    if p["balance"] < price:
        await callback.answer("❌ Недостаточно денег!", show_alert=True)
        return

    # Проверяем кидалово
    if random.randint(1, 100) <= supplier["scam_chance"]:
        p["balance"] -= price
        p["total_spent"] += price
        p["scam_times"] += 1
        p["reputation"] = max(0, p["reputation"] - 5)
        await callback.message.edit_text(
            f"💀 <b>ТЕБЯ КИНУЛИ!</b>\n\n"
            f"{supplier['name']} взял деньги и пропал.\n"
            f"Потеряно: {price}₽\n"
            f"Баланс: {p['balance']}₽",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
            ])
        )
        await check_game_over(callback, p)
        return

    # Успешная покупка
    p["balance"] -= price
    p["total_spent"] += price
    demand = p["market_demand"].get(item["cat"], 1.0)
    market_price = get_market_price(item["base_price"], demand)

    p["inventory"].append({
        "name": f"{item['cat']} {item['name']}",
        "cat": item["cat"],
        "buy_price": price,
        "market_price": market_price,
        "base_price": item["base_price"],
    })

    await callback.message.edit_text(
        f"✅ <b>ТОВАР КУПЛЕН!</b>\n\n"
        f"📦 {item['cat']} {item['name']}\n"
        f"💰 Закуп: {price}₽\n"
        f"📊 Рынок: ~{market_price}₽\n"
        f"💼 Баланс: {p['balance']}₽\n"
        f"📦 В инвентаре: {len(p['inventory'])} товаров",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Купить ещё", callback_data=f"supplier_{supplier_idx}")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
        ])
    )

# ==================== ИНВЕНТАРЬ И ПРОДАЖА ====================

@dp.callback_query(F.data == "action_inventory")
async def show_inventory(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)

    if not p["inventory"]:
        await callback.message.edit_text(
            "📦 Инвентарь пуст. Закупись у поставщиков!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏭 К поставщикам", callback_data="action_buy")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
            ])
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{item['name']} | Закуп: {item['buy_price']}₽ | ~{item['market_price']}₽",
            callback_data=f"sell_{i}"
        )] for i, item in enumerate(p["inventory"])
    ] + [[InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]])

    inv_text = "📦 <b>ТВОЙ ИНВЕНТАРЬ:</b>\n" + "\n".join(
        [f"{i+1}. {item['name']} | Закуп: {item['buy_price']}₽ | ~{item['market_price']}₽" 
         for i, item in enumerate(p["inventory"])]
    )
    await callback.message.edit_text(
        inv_text + "\n\nВыбери товар для продажи:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@dp.callback_query(F.data.startswith("sell_"))
async def try_sell_item(callback: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    p = get_player(user_id)

    if item_idx >= len(p["inventory"]):
        await callback.answer("Товар не найден.")
        return

    item = p["inventory"][item_idx]
    buyer_name = random.choice(BUYER_NAMES)
    demand = p["market_demand"].get(item["cat"], 1.0)
    interest_chance = min(0.9, demand * 0.6)

    if random.random() > interest_chance:
        await callback.message.edit_text(
            f"👤 {buyer_name}: Не, {item['cat']} сейчас не интересно. Давай другое.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 В инвентарь", callback_data="action_inventory")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
            ])
        )
        return

    offer_mult = random.uniform(0.7, 1.1)
    offer_price = int(item["market_price"] * offer_mult)

    await state.update_data(selling_item_idx=item_idx, buyer_offer=offer_price, buyer_name=buyer_name)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласиться", callback_data="accept_offer")],
        [InlineKeyboardButton(text="📈 Торговаться (+10%)", callback_data="haggle_up")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="decline_offer")],
    ])

    await callback.message.edit_text(
        f"👤 <b>{buyer_name}</b> хочет купить {item['name']}\n"
        f"💰 Закуп: {item['buy_price']}₽ | Рынок: ~{item['market_price']}₽\n\n"
        f"Предлагает: <b>{offer_price}₽</b>\n\nТвой ответ:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

@dp.callback_query(F.data == "accept_offer")
async def accept_offer(callback: types.CallbackQuery, state: FSMContext):
    await complete_sale(callback, state, 0)

@dp.callback_query(F.data == "haggle_up")
async def haggle_up(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    buyer_name = data.get("buyer_name", "Покупатель")
    offer = data.get("buyer_offer", 0)
    new_offer = int(offer * 1.1)
    user_id = callback.from_user.id
    p = get_player(user_id)
    haggle_chance = 0.3 + (p["reputation"] / 100) * 0.4

    if random.random() < haggle_chance:
        await state.update_data(buyer_offer=new_offer)
        await complete_sale(callback, state, new_offer - offer)
    else:
        await callback.message.edit_text(
            f"👤 {buyer_name}: ❌ Не, так не пойдёт. Я пошёл.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 В инвентарь", callback_data="action_inventory")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
            ])
        )

@dp.callback_query(F.data == "decline_offer")
async def decline_offer(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Ты отказался от предложения.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 В инвентарь", callback_data="action_inventory")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
        ])
    )

async def complete_sale(callback: types.CallbackQuery, state: FSMContext, haggle_bonus):
    data = await state.get_data()
    item_idx = data.get("selling_item_idx", 0)
    buyer_name = data.get("buyer_name", "Покупатель")
    final_offer = data.get("buyer_offer", 0)
    user_id = callback.from_user.id
    p = get_player(user_id)

    if item_idx >= len(p["inventory"]):
        await callback.answer("Ошибка. Товар уже продан.")
        return

    item = p["inventory"].pop(item_idx)
    p["balance"] += final_offer
    profit = final_offer - item["buy_price"]
    p["total_earned"] += profit
    p["items_sold"] += 1
    p["stat_earned_today"] += profit
    p["stat_sold_today"] += 1
    p["reputation"] = min(100, p["reputation"] + random.randint(1, 5))

    haggle_text = f"\n🔥 Выторговал +{haggle_bonus}₽!" if haggle_bonus > 0 else ""

    await callback.message.edit_text(
        f"✅ <b>ПРОДАНО!</b>\n\n"
        f"📦 {item['name']}\n"
        f"👤 Покупатель: {buyer_name}\n"
        f"💰 Цена: {final_offer}₽\n"
        f"💵 Прибыль: {profit}₽{haggle_text}\n"
        f"💼 Баланс: {p['balance']}₽\n"
        f"⭐ Репутация: {p['reputation']}/100",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 В инвентарь", callback_data="action_inventory")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
        ])
    )
    await check_game_over(callback, p)

# ==================== СТАТИСТИКА И ДНИ ====================

@dp.callback_query(F.data == "action_stats")
async def show_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)

    demand_lines = []
    for cat, mult in p["market_demand"].items():
        emoji = "📈" if mult > 1.0 else "📉" if mult < 1.0 else "➡️"
        demand_lines.append(f"{emoji} {cat}: x{mult:.1f}")

    await callback.message.edit_text(
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"💰 Баланс: {p['balance']}₽\n"
        f"⭐ Репутация: {p['reputation']}/100\n"
        f"📅 День: {p['day']}\n"
        f"📦 В инвентаре: {len(p['inventory'])} товаров\n"
        f"💸 Заработано всего: {p['total_earned']}₽\n"
        f"🛒 Потрачено на закуп: {p['total_spent']}₽\n"
        f"📋 Продано: {p['items_sold']} шт.\n"
        f"⚠️ Кинули раз: {p['scam_times']}\n\n"
        f"📊 <b>СПРОС:</b>\n" + "\n".join(demand_lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="action_back")]
        ])
    )

@dp.callback_query(F.data == "action_nextday")
async def next_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)

    day_summary = (
        f"🌙 <b>ИТОГИ ДНЯ {p['day']}</b>\n"
        f"💰 Заработано: {p['stat_earned_today']}₽\n"
        f"📋 Продано: {p['stat_sold_today']} шт.\n"
        f"💼 Баланс: {p['balance']}₽"
    )

    p["day"] += 1
    p["stat_earned_today"] = 0
    p["stat_sold_today"] = 0

    for cat in CATEGORIES:
        p["market_demand"][cat] *= random.uniform(0.85, 1.15)
        p["market_demand"][cat] = max(0.3, min(3.0, p["market_demand"][cat]))

    event = generate_daily_event()
    p["current_event"] = event
    if event:
        apply_market_event(p, event)

    event_text = f"\n\n{event['text']}" if event else ""

    if p["inventory"] and random.random() < 0.2:
        for item in p["inventory"]:
            item["market_price"] = int(item["market_price"] * random.uniform(0.7, 0.95))
        event_text += "\n\n⚠️ Некоторые товары в инвентаре потеряли в цене (залежались)."

    await callback.message.edit_text(
        f"{day_summary}\n\n☀️ <b>ДЕНЬ {p['day']}</b>{event_text}\n\nВыбери действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "action_end")
async def end_game(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    p = get_player(user_id)
    await state.clear()

    if p["balance"] >= 50000:
        result = "🏆 <b>ПОБЕДА!</b> Ты раскрутился до 50 000₽!"
    elif p["balance"] <= 0:
        result = "💀 <b>БАНКРОТ!</b> Деньги кончились."
    else:
        result = "🎮 Игра окончена."

    await callback.message.edit_text(
        f"{result}\n\n"
        f"💰 Баланс: {p['balance']}₽\n"
        f"📅 Дней: {p['day']}\n"
        f"💸 Заработано: {p['total_earned']}₽\n"
        f"📋 Продано: {p['items_sold']} шт.\n\n"
        f"Хочешь в реальность? Заходи в @vintagedrop61 — бери вещи на реализацию!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Сыграть ещё", callback_data="restart_game")]
        ])
    )

@dp.callback_query(F.data == "restart_game")
async def restart_game(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in players:
        del players[user_id]
    await callback.message.edit_text("Перезапуск... Напиши /play для новой игры!")

@dp.callback_query(F.data == "action_back")
async def back_to_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    event = p.get("current_event")
    event_text = f"\n\n{event['text']}" if event else ""
    await callback.message.edit_text(
        f"📅 <b>День {p['day']}</b> | 💰 {p['balance']}₽{event_text}\n\nВыбери действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

async def check_game_over(callback, p):
    if p["balance"] >= 50000:
        await callback.message.answer(
            f"🏆 <b>ПОЗДРАВЛЯЮ!</b> Ты достиг 50 000₽!\n"
            f"Готов к реальным продажам? @vintagedrop61",
            parse_mode=ParseMode.HTML
        )
    elif p["balance"] <= 0:
        await callback.message.answer(
            f"💀 <b>БАНКРОТ</b>\n"
            f"Это игра. В реальности начни без вложений в @vintagedrop61\n"
            f"Напиши /play чтобы сыграть снова.",
            parse_mode=ParseMode.HTML
        )

# ==================== ЗАПУСК ====================
async def main():
    print("🎮 ReSell Tycoon запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())