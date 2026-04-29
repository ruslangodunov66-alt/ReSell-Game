import asyncio
import logging
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from settings import BOT_TOKEN, ADMIN_IDS

# Имитация базы данных (для простоты — в памяти)
# В реальном проекте используйте SQLite, как в предыдущих версиях
users = {}
inventory = {}
market = []

# Генерация товаров с брендами и сезонами
def generate_products():
    seasons = ["весна", "лето", "осень", "зима", "всесезон"]
    products = []
    # Куртки
    brands_coats = ["Canada Goose", "The North Face", "Moncler", "Patagonia"]
    for brand in brands_coats:
        products.append((f"{brand} пуховик", brand, random.randint(8000, 30000), random.choice(["осень", "зима"])))
        products.append((f"{brand} ветровка", brand, random.randint(3000, 12000), random.choice(["весна", "лето", "осень"])))
    # Электроника
    brands_elec = ["Apple", "Samsung", "Xiaomi", "Sony"]
    for brand in brands_elec:
        products.append((f"{brand} наушники", brand, random.randint(2000, 15000), "всесезон"))
        products.append((f"{brand} смартфон", brand, random.randint(15000, 80000), "всесезон"))
        products.append((f"{brand} часы", brand, random.randint(5000, 25000), "всесезон"))
    # Часы
    brands_watch = ["Rolex", "Casio", "Seiko", "Tissot"]
    for brand in brands_watch:
        products.append((f"{brand} часы", brand, random.randint(3000, 150000), "всесезон"))
    # Вещи
    brands_cloth = ["Nike", "Adidas", "Puma", "Zara"]
    for brand in brands_cloth:
        products.append((f"{brand} футболка", brand, random.randint(1500, 6000), "лето"))
        products.append((f"{brand} джинсы", brand, random.randint(2000, 10000), "всесезон"))
        products.append((f"{brand} кроссовки", brand, random.randint(3000, 18000), random.choice(["весна", "лето", "осень"])))
    return products

def generate_market():
    global market
    market = []
    products = generate_products()
    for prod, brand, price, season in products[:30]:
        final_price = int(price * random.uniform(0.8, 1.5))
        market.append({
            'product': f"{brand} {prod}",
            'price': final_price,
            'season': season,
            'base_price': price
        })

def init_user(user_id, username):
    if user_id not in users:
        users[user_id] = {
            'username': username,
            'balance': 1000,
            'level': 1,
            'exp': 0,
            'sell_skill': 1,
            'buy_skill': 1,
            'wins': 0,
            'losses': 0,
            'referrals': 0
        }
        inventory[user_id] = {}
        # Стартовый инвентарь (2 товара)
        for _ in range(2):
            prod = random.choice(generate_products())
            inv_name = f"{prod[1]} {prod[0]}"
            inventory[user_id][inv_name] = inventory[user_id].get(inv_name, 0) + 1

def get_user(user_id):
    return users.get(user_id)

def update_user(user_id, **kwargs):
    if user_id in users:
        for key, value in kwargs.items():
            if key in users[user_id]:
                users[user_id][key] = value

def add_exp(user_id, amount):
    user = get_user(user_id)
    if not user:
        return None
    new_exp = user['exp'] + amount
    exp_needed = user['level'] * 100
    if new_exp >= exp_needed:
        new_level = user['level'] + 1
        new_exp -= exp_needed
        update_user(user_id, level=new_level, exp=new_exp)
        return new_level
    else:
        update_user(user_id, exp=new_exp)
        return None

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
generate_market()

# ---------- КЛАВИАТУРЫ ----------
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить у поставщиков", callback_data="buy_menu")],
        [InlineKeyboardButton(text="💰 Продать товар", callback_data="sell_menu")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="🏆 Лидеры", callback_data="leaders")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    init_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "🧑‍💼 *Торговый симулятор*\n\n"
        "Покупай товары у поставщиков, продавай клиентам с наценкой.\n"
        "Прокачивай навыки и стань лидером!\n\n"
        "👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )

# ---------- ПОКУПКА ----------
@dp.callback_query(F.data == "buy_menu")
async def buy_menu(callback: types.CallbackQuery):
    if not market:
        await callback.message.edit_text("⚠️ Рынок пуст. Попробуйте позже.")
        await callback.answer()
        return

    text = "🛒 *Товары от поставщиков:*\n\n"
    for i, item in enumerate(market[:15]):
        text += f"📦 {item['product']}\n💰 {item['price']} 💎\n🍂 Сезон: {item['season']}\n\n"

    keyboard = []
    for i, item in enumerate(market[:15]):
        keyboard.append([InlineKeyboardButton(text=f"Купить {item['product']}", callback_data=f"buy_{i}")])
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить рынок (20 💎)", callback_data="refresh_market")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])

    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "refresh_market")
async def refresh_market(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or user['balance'] < 20:
        await callback.answer("❌ Не хватает 20 💎 для обновления!", show_alert=True)
        return
    update_user(callback.from_user.id, balance=user['balance'] - 20)
    generate_market()
    await callback.answer("✅ Рынок обновлён!", show_alert=True)
    await buy_menu(callback)

@dp.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: types.CallbackQuery):
    idx = int(callback.data.split("_")[1])
    product = market[idx]['product']
    price = market[idx]['price']
    user = get_user(callback.from_user.id)
    buy_skill = user['buy_skill']
    discount = min(buy_skill * 0.02, 0.3)
    final_price = int(price * (1 - discount))

    await callback.message.answer(
        f"💎 *Покупка: {product}*\n"
        f"Цена: {final_price} 💎\n"
        f"Введите количество (1-99):",
        parse_mode=ParseMode.MARKDOWN
    )
    # Сохраняем выбранный товар
    callback.bot.data = {'temp_product': product, 'temp_price': final_price}
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and 1 <= int(msg.text) <= 99)
async def process_quantity(message: types.Message):
    user_id = message.from_user.id
    quantity = int(message.text)
    if not hasattr(message.bot, 'data') or 'temp_product' not in message.bot.data:
        await message.answer("❌ Пожалуйста, начните покупку заново через меню.")
        return

    product = message.bot.data['temp_product']
    price_per_unit = message.bot.data['temp_price']
    total_cost = price_per_unit * quantity
    user = get_user(user_id)

    if user['balance'] < total_cost:
        await message.answer(f"❌ Не хватает {total_cost} 💎")
        return

    # Покупка
    update_user(user_id, balance=user['balance'] - total_cost)
    if user_id not in inventory:
        inventory[user_id] = {}
    inventory[user_id][product] = inventory[user_id].get(product, 0) + quantity

    await message.answer(f"✅ Куплено {product} x{quantity} за {total_cost} 💎\nВаш баланс: {user['balance'] - total_cost} 💎")
    del message.bot.data['temp_product']
    del message.bot.data['temp_price']

# ---------- ПРОДАЖА С ИМЕНАМИ КЛИЕНТОВ ----------
@dp.callback_query(F.data == "sell_menu")
async def sell_menu(callback: types.CallbackQuery):
    user_inv = inventory.get(callback.from_user.id, {})
    if not user_inv:
        await callback.message.edit_text("📭 *Инвентарь пуст.* Купите товары у поставщиков.", parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
        await callback.answer()
        return

    text = "📦 *Ваши товары:*\n\n"
    for product, qty in user_inv.items():
        text += f"• {product} — {qty} шт.\n"

    keyboard = [[InlineKeyboardButton(text=f"Продать {product}", callback_data=f"sell_{product}")] for product in user_inv.keys()]
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])

    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_"))
async def prepare_sale(callback: types.CallbackQuery):
    product = callback.data[5:]
    user = get_user(callback.from_user.id)
    sell_skill = user['sell_skill']
    # Поиск базовой цены товара
    base_price = 5000
    for item in market:
        if item['product'] == product:
            base_price = item['base_price']
            break

    skill_multiplier = 1 + sell_skill * 0.05
    random_factor = random.uniform(0.7, 1.3)
    offer_price = int(base_price * skill_multiplier * random_factor)
    offer_price = max(offer_price, 100)

    customers = ["Анна", "Михаил", "Екатерина", "Дмитрий", "Ольга", "Сергей", "Татьяна", "Алексей"]
    customer = random.choice(customers)

    # Сохраняем предложение (временно)
    callback.bot.data['temp_offer'] = {'user_id': callback.from_user.id, 'product': product, 'price': offer_price, 'customer': customer}
    await callback.answer(f"👤 {customer} предлагает {offer_price} 💎 за {product}!\nИспользуйте /sell_confirm для принятия.", show_alert=True)

@dp.message(Command("sell_confirm"))
async def confirm_sale(message: types.Message):
    user_id = message.from_user.id
    if not hasattr(message.bot, 'data') or 'temp_offer' not in message.bot.data:
        await message.answer("❌ Нет активного предложения. Сначала выберите товар для продажи.")
        return

    offer = message.bot.data['temp_offer']
    if offer['user_id'] != user_id:
        await message.answer("❌ Это предложение не для вас.")
        return

    product = offer['product']
    price = offer['price']
    customer = offer['customer']

    if user_id not in inventory or inventory[user_id].get(product, 0) < 1:
        await message.answer("❌ Товар уже продан или его нет в инвентаре.")
        return

    # Продажа
    inventory[user_id][product] -= 1
    if inventory[user_id][product] == 0:
        del inventory[user_id][product]

    user = get_user(user_id)
    update_user(user_id, balance=user['balance'] + price)
    level_up = add_exp(user_id, 25)

    msg = f"✅ Продажа {product} клиенту {customer} за {price} 💎 совершена!\n📈 Опыт +25"
    if level_up:
        msg += f"\n🎉 *Уровень повышен до {level_up}!*"
    await message.answer(msg, parse_mode=ParseMode.MARKDOWN)
    del message.bot.data['temp_offer']

# ---------- ПРОФИЛЬ ----------
@dp.callback_query(F.data == "my_profile")
async def my_profile(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Данные профиля не найдены! Попробуйте /start", show_alert=True)
        return
    text = (
        "👤 *Ваш профиль*\n\n"
        f"💰 Баланс: {user['balance']} 💎\n"
        f"📊 Уровень: {user['level']}\n"
        f"⭐ Опыт: {user['exp']}/{user['level']*100}\n"
        f"🤝 Навык продаж: {user['sell_skill']}\n"
        f"📦 Навык закупок: {user['buy_skill']}\n"
        f"👥 Приглашено друзей: {user.get('referrals', 0)}\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Повысить навык продаж (200 опыта)", callback_data="up_sell")],
        [InlineKeyboardButton(text="🏭 Повысить навык закупок (200 опыта)", callback_data="up_buy")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "up_sell")
async def upgrade_sell(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка профиля", show_alert=True)
        return
    if user['sell_skill'] >= 10:
        await callback.answer("✅ Навык продаж уже максимальный (10)!", show_alert=True)
        return
    if user['exp'] < 200:
        await callback.answer("❌ Не хватает 200 опыта!", show_alert=True)
        return
    new_skill = user['sell_skill'] + 1
    new_exp = user['exp'] - 200
    update_user(callback.from_user.id, sell_skill=new_skill, exp=new_exp)
    await callback.answer(f"✅ Навык продаж повышен до {new_skill}!", show_alert=True)
    await my_profile(callback)

@dp.callback_query(F.data == "up_buy")
async def upgrade_buy(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка профиля", show_alert=True)
        return
    if user['buy_skill'] >= 10:
        await callback.answer("✅ Навык закупок уже максимальный (10)!", show_alert=True)
        return
    if user['exp'] < 200:
        await callback.answer("❌ Не хватает 200 опыта!", show_alert=True)
        return
    new_skill = user['buy_skill'] + 1
    new_exp = user['exp'] - 200
    update_user(callback.from_user.id, buy_skill=new_skill, exp=new_exp)
    await callback.answer(f"✅ Навык закупок повышен до {new_skill}!", show_alert=True)
    await my_profile(callback)

# ---------- ЛИДЕРЫ ----------
@dp.callback_query(F.data == "leaders")
async def leaders(callback: types.CallbackQuery):
    sorted_users = sorted(users.values(), key=lambda x: x['balance'], reverse=True)[:10]
    text = "🏅 *ТОП предпринимателей*\n\n"
    for i, u in enumerate(sorted_users, 1):
        text += f"{i}. @{u['username']} — {u['balance']} 💎 (уровень {u['level']})\n"
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

# ---------- НАЗАД ----------
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🧑‍💼 *Торговый симулятор*\n\n👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )
    await callback.answer()

async def main():
    print("🚀 Торговый симулятор с клиентами запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())