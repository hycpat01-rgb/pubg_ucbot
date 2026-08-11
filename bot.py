import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================
TOKEN = "8892100518:AAFJ6-7pM2hwP9LEJkAPwOloaqiaku9Dy7w"
ADMIN_CHAT_ID = 1231002682

SBP_DETAILS = "💳 **Сбер / Т-Банк (СБП):**\n`+7 (963) 258 78 84`\n(Получатель: Нусратулло Носиров.)"
ASIA_DETAILS = "🌏 **Карты стран Азии:**\nНомер карты: `4400 0555 3145 2345`\n(Душанбе Сити)"
ADMIN_USERNAME = "@arrhiv1"
# ===================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def db_start():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            player_id TEXT,
            balance REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()

db_start()

class PurchaseState(StatesGroup):
    waiting_for_player_id = State()
    waiting_for_topup_amount = State()
    waiting_for_screenshot = State()
    waiting_for_payment_screenshot = State()

UC_PRICES = {
    "60": 90.0,
    "325": 450.0,
    "660": 900.0,
    "1800": 2300.0,
    "3850": 4600.0,
    "8100": 9200.0
}

async def auto_buy_uc_from_official_site(player_id: str, uc_type: str) -> bool:
    await asyncio.sleep(2)
    return True

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 0.0)", (user_id, username))
    conn.commit()
    conn.close()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить UC", callback_data="buy_uc")
    builder.button(text="👤 Мой профиль", callback_data="profile")
    builder.button(text="🛠 Поддержка", callback_data="support")
    builder.adjust(1, 2)
    
    await message.answer(
        "👋 **Добро пожаловать в официальный бот по покупке UC!**\n\nВыберите нужный раздел:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_uc")
async def uc_packages(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    for uc, price in UC_PRICES.items():
        builder.button(text=f"{uc} UC - {int(price)} ₽", callback_data=f"uc_{uc}")
    builder.button(text="⬅️ Назад", callback_data="back_home")
    builder.adjust(2, 2, 2, 1)
    
    await callback.message.edit_text(
        "📦 **Выберите нужный пакет UC:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("uc_"))
async def select_uc(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uc_type = callback.data.split("_")[1]
    await state.update_data(chosen_uc=uc_type)
    
    await callback.message.answer(
        "🆔 Пожалуйста, введите ваш **Player ID** в PUBG Mobile:\n(Пример: `5123456789`)",
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseState.waiting_for_player_id)

@dp.message(PurchaseState.waiting_for_player_id)
async def process_player_id(message: types.Message, state: FSMContext):
    player_id = message.text.strip()
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    price = UC_PRICES.get(chosen_uc, 0)
    user_id = message.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET player_id = ? WHERE user_id = ?", (player_id, user_id))
    conn.commit()
    
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить переводом ({int(price)} ₽)", callback_data=f"pay_card_{chosen_uc}")
    if balance >= price:
        builder.button(text=f"💰 Оплатить с баланса ({int(price)} ₽)", callback_data=f"pay_bal_{chosen_uc}")
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.adjust(1)

    await message.answer(
        f"✅ **Данные сохранены!**\n\n📦 Пакет: **{chosen_uc} UC**\n🆔 ID: `{player_id}`\n💰 Баланс: **{balance} ₽**\n\nВыберите способ оплаты:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card_request(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uc_type = callback.data.split("_")[2]
    price = UC_PRICES.get(uc_type, 0)
    
    await state.update_data(chosen_uc=uc_type, price=price, pay_type="Перевод")
    await state.set_state(PurchaseState.waiting_for_payment_screenshot)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data="buy_uc")
    
    await callback.message.edit_text(
        f"💳 **Оплата заказа ({uc_type} UC)**\n\nСумма: **{int(price)} ₽**\n\n{SBP_DETAILS}\n\n📸 **Отправьте скриншот чека** в этот чат:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(PurchaseState.waiting_for_payment_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    price = data.get("price")
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    photo_id = message.photo[-1].file_id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    player_id = row[0] if row else "Не найден"
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Заказ выполнен", callback_data=f"done_{user_id}_{chosen_uc}")
    builder.adjust(1)
    
    await bot.send_photo(
        ADMIN_CHAT_ID,
        photo=photo_id,
        caption=f"🛒 **НОВЫЙ ЗАКАЗ НА UC!**\n\n👤 От: @{username} (`{user_id}`)\n🆔 Игр. ID: `{player_id}`\n📦 Пакет: {chosen_uc} UC\n💵 Сумма: {int(price)} ₽",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await message.answer("✅ **Скриншот отправлен администратору!** Ожидайте выполнения заказа.", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("done_"))
async def admin_done(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    chosen_uc = parts[2]
    
    try:
        await bot.send_message(user_id, f"🎉 **Ваш заказ на {chosen_uc} UC выполнен!** Проверьте игру.", parse_mode="Markdown")
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ **СТАТУС: Заказ выполнен**", reply_markup=None)
    await callback.answer("Заказ отмечен выполненным!")

@dp.callback_query(F.data == "top_up")
async def top_up_balance(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 СБП / Карты РФ", callback_data="method_sbp")
    builder.button(text="🌏 Карты Азии", callback_data="method_asia")
    builder.button(text="⬅️ Назад", callback_data="profile")
    builder.adjust(1)
    
    await callback.message.edit_text("💳 **Пополнение баланса**\n\nВыберите способ перевода:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("method_"))
async def method_select(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    method = callback.data.split("_")[1]
    details = SBP_DETAILS if method == "sbp" else ASIA_DETAILS
    
    await state.update_data(method=method)
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data="top_up")
    
    await callback.message.edit_text(f"{details}\n\n💵 **Введите сумму пополнения в рублях:**\n(Пример: `500`)", reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(PurchaseState.waiting_for_topup_amount)

@dp.message(PurchaseState.waiting_for_topup_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное число (например, `500`):", parse_mode="Markdown")
        return
        
    await state.update_data(topup_amount=amount)
    await state.set_state(PurchaseState.waiting_for_screenshot)
    
    await message.answer(f"✅ Сумма: **{amount} ₽**\n\n📸 Теперь **отправьте скриншот чека** в этот чат:", parse_mode="Markdown")

@dp.message(PurchaseState.waiting_for_screenshot, F.photo)
async def process_topup_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("topup_amount")
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Зачислить баланс", callback_data=f"conf_{user_id}_{amount}")
    builder.adjust(1)
    
    await bot.send_photo(
        ADMIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=f"🔔 **Заявка на пополнение баланса!**\n\n👤 От: @{username} (`{user_id}`)\n💵 Сумма: **{amount} ₽**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await message.answer("✅ **Скриншот отправлен администратору!** Ожидайте зачисления средств.", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("conf_"))
async def confirm_topup(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    amount = float(parts[2])
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    new_balance = row[0] if row else amount
    conn.close()
    
    try:
        await bot.send_message(user_id, f"🎉 **Ваш баланс успешно пополнен!**\n\n➕ Зачислено: **{amount} ₽**\n💰 Новый баланс: **{new_balance} ₽**", parse_mode="Markdown")
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ **СТАТУС: Зачислено ({amount} ₽)**", reply_markup=None)
    await callback.answer("Баланс успешно зачислен!")

@dp.callback_query(F.data == "profile")
async def profile(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    player_id = row[0] if row and row[0] else "Не указан ❌"
    balance = row[1] if row and row[1] is not None else 0.0
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.button(text="⬅️ Назад", callback_data="back_home")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"👤 **Ваш профиль:**\n\n🆔 Telegram ID: `{user_id}`\n🎮 PUBG Player ID: `{player_id}`\n💰 Баланс: **{balance} ₽**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить UC", callback_data="buy_uc")
    builder.button(text="👤 Мой профиль", callback_data="profile")
    builder.button(text="🛠 Поддержка", callback_data="support")
    builder.adjust(1, 2)
    
    await callback.message.edit_text("👋 **Главное меню:**\n\nВыберите нужный раздел:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(f"🛠 Для связи с администратором: {ADMIN_USERNAME}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
