import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

import game_db
from settings import BOT_TOKEN, ADMIN_IDS

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
game_db.init_db()

# ---------- КЛАВИАТУРЫ ----------
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Купить товар", callback_data="buy_menu")],
        [InlineKeyboardButton(text="📦 Мой инвентарь", callback_data="my_inventory")],
        [InlineKeyboardButton(text="💰 Продать товар", callback_data="sell_menu")],
        [InlineKeyboardButton(text="🏆 Лидеры", callback_data="leaders")],
        [InlineKeyboardButton(text="📊 Мой бизнес", callback_data="my_business")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    game_db.register_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "🧑‍💼 *Добро пожаловать в товарный бизнес!*\n\n"
        "📈 Покупай товары по выгодной цене\n"
        "💰 Продавай, когда цена вырастет\n"
        "🤝 Приглашай друзей — ускоряй прокачку!\n"
        "📊 Прокачивай навыки и становись лидером\n\n"
        "👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )

# ---------- КУПИТЬ ТОВАР ----------
@dp.callback_query(F.data == "buy_menu")
async def buy_menu(callback: types.CallbackQuery):
    offers = game_db.get_market_offers()
    if not offers:
        await callback.message.edit_text("⚠️ Рынок пуст. Попробуйте позже.")
        await callback.answer()
        return
    text = "🛒 *Доступные товары для покупки:*\n\n"
    for o in offers:
        exp_date = datetime.strptime(o['expires_at'], "%Y-%m-%d %H:%M:%S.%f")
        text += f"📦 *{o['product']}*\n💰 {o['price']} 💎\n📊 Спрос: {o['demand']}\n⏳ До {exp_date.strftime('%d.%m %H:%M')}\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить рынок (10 💎)", callback_data="refresh_market")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "refresh_market")
async def refresh_market(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user or user['balance'] < 10:
        await callback.answer("❌ Не хватает 10 💎 для обновления!", show_alert=True)
        return
    game_db.update_user(callback.from_user.id, balance=user['balance'] - 10)
    game_db.generate_market()
    await callback.answer("✅ Рынок обновлён!", show_alert=True)
    await buy_menu(callback)

# ---------- ИНВЕНТАРЬ ----------
@dp.callback_query(F.data == "my_inventory")
async def my_inventory(callback: types.CallbackQuery):
    inv = game_db.get_inventory(callback.from_user.id)
    if not inv:
        await callback.message.edit_text("📭 *Ваш инвентарь пуст.*\nКупите товары в разделе «Купить товар».", parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
        await callback.answer()
        return
    text = "📦 *Ваш инвентарь:*\n\n"
    for item in inv:
        text += f"• {item['product']} — {item['quantity']} шт.\n"
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

# ---------- ПРОДАЖА ТОВАРА (через покупателей) ----------
@dp.callback_query(F.data == "sell_menu")
async def sell_menu(callback: types.CallbackQuery):
    inv = game_db.get_inventory(callback.from_user.id)
    if not inv:
        await callback.message.edit_text("📭 *Нет товаров для продажи.*", parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
        await callback.answer()
        return
    keyboard = []
    for item in inv:
        keyboard.append([InlineKeyboardButton(text=f"Продать {item['product']} (x{item['quantity']})", callback_data=f"choose_{item['product']}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    await callback.message.edit_text("💰 *Выберите товар для продажи:*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data.startswith("choose_"))
async def choose_product(callback: types.CallbackQuery):
    product = callback.data.split("_", 1)[1]
    # запоминаем выбранный товар во временном хранилище
    game_db.set_temp_product(callback.from_user.id, product)
    # генерируем покупателя
    buyer_price, required_skill, buyer_name = game_db.generate_random_buyer(product)
    user = game_db.get_user(callback.from_user.id)
    if user['sell_skill'] < required_skill:
        await callback.answer(f"❌ {buyer_name} требует навык продаж {required_skill}. Прокачайтесь!", show_alert=True)
        return
    await callback.answer(f"👤 {buyer_name} предлагает {buyer_price} 💎 за {product}.\nИспользуйте /sell_confirm для подтверждения сделки.", show_alert=True)
    # сохраняем предложение в БД
    game_db.save_offer(callback.from_user.id, product, buyer_price)

@dp.message(Command("sell_confirm"))
async def confirm_sale(message: types.Message):
    user_id = message.from_user.id
    offer = game_db.get_offer(user_id)
    if not offer:
        await message.answer("❌ Нет активного предложения. Сначала выберите товар в разделе «Продать товар».")
        return
    product, price = offer
    if not game_db.remove_from_inventory(user_id, product):
        await message.answer("❌ Товар уже продан или закончился.")
        return
    game_db.update_user(user_id, balance=game_db.get_user(user_id)['balance'] + price)
    game_db.add_exp(user_id, 20)
    game_db.earn_achievement(user_id, "Первая продажа")
    await message.answer(f"✅ Продажа {product} за {price} 💎 совершена!")
    game_db.clear_offer(user_id)

# ---------- БИЗНЕС-СТАТИСТИКА И ПРОКАЧКА ----------
@dp.callback_query(F.data == "my_business")
async def my_business(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка данных")
        return
    text = (
        "🏢 *Твой бизнес*\n\n"
        f"💰 Баланс: {user['balance']} 💎\n"
        f"📊 Уровень: {user['level']}\n"
        f"⭐ Опыт: {user['exp']}/{user['level']*100}\n"
        f"🤝 Навык продаж: {user['sell_skill']}\n"
        f"📦 Навык закупок: {user['buy_skill']}\n"
        f"👥 Приглашено друзей: {user['referrals']}\n"
        f"🏆 Побед: {user['wins']}\n"
        f"😞 Поражений: {user['losses']}\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Прокачать навык продаж", callback_data="up_sell")],
        [InlineKeyboardButton(text="🏭 Прокачать навык закупок", callback_data="up_buy")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "up_sell")
async def upgrade_sell(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return
    if user['sell_skill'] >= 10:
        await callback.answer("✅ Навык продаж уже максимальный (10)!", show_alert=True)
        return
    # Проверка: либо 2 часа в игре, либо 3 друга
    play_hours = (datetime.now() - user['last_play']).total_seconds() / 3600
    if play_hours < 2 and user['referrals'] < 3:
        await callback.answer("❌ Требуется: 2 часа в игре или 3 приглашённых друга.", show_alert=True)
        return
    new_skill = user['sell_skill'] + 1
    game_db.update_user(callback.from_user.id, sell_skill=new_skill)
    await callback.answer(f"✅ Навык продаж повышен до {new_skill}!", show_alert=True)
    await my_business(callback)

@dp.callback_query(F.data == "up_buy")
async def upgrade_buy(callback: types.CallbackQuery):
    user = game_db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка")
        return
    if user['buy_skill'] >= 10:
        await callback.answer("✅ Навык закупок уже максимальный (10)!", show_alert=True)
        return
    play_hours = (datetime.now() - user['last_play']).total_seconds() / 3600
    if play_hours < 2 and user['referrals'] < 3:
        await callback.answer("❌ Требуется: 2 часа в игре или 3 приглашённых друга.", show_alert=True)
        return
    new_skill = user['buy_skill'] + 1
    game_db.update_user(callback.from_user.id, buy_skill=new_skill)
    await callback.answer(f"✅ Навык закупок повышен до {new_skill}!", show_alert=True)
    await my_business(callback)

# ---------- ЛИДЕРЫ ----------
@dp.callback_query(F.data == "leaders")
async def leaders(callback: types.CallbackQuery):
    conn = game_db.sqlite3.connect(game_db.DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT username, balance, level FROM users ORDER BY balance DESC LIMIT 10')
    rows = cur.fetchall()
    conn.close()
    text = "🏅 *ТОП предпринимателей*\n\n"
    for i, (uname, bal, lvl) in enumerate(rows, 1):
        text += f"{i}. @{uname} — {bal} 💎 (уровень {lvl})\n"
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

# ---------- НАЗАД ----------
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🧑‍💼 *Товарный бизнес*\n\n👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )
    await callback.answer()

# ---------- ЗАПУСК ----------
async def main():
    print("🚀 Товарный бизнес-бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())