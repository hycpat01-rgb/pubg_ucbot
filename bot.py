import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ (РЕКВИЗИТЫ) ====================
TOKEN = "8892100518:AAFJ6-7pM2hwP9LEJkAPwOloaqiaku9Dy7w"

# Изменяйте реквизиты для оплаты здесь в любой момент:
SBP_DETAILS = "💳 **Сбер / Т-Банк (СБП):**\n`+7 (999) 000-00-00`\n(Получатель: Имя Ф.)"
ASIA_DETAILS = "🌏 **Карты стран Азии (Казахстан / Узбекистан / др.):**\nНомер карты: `4400 0000 0000 0000`\n(Банк / Получатель)"

ADMIN_USERNAME = "@arrhiv1"
# ===============================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------- БАЗА ДАННЫХ (SQLite) -----------------
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

# ----------------- КОМАНДА /START -----------------
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
        "👋 **Добро пожаловать в официальный бот по покупке UC!**\n\n"
        "Пожалуйста, выберите нужный раздел:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# ----------------- МЕНЮ ПОКУПКИ UC -----------------
@dp.callback_query(F.data == "buy_uc")
async def uc_packages(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="60 UC - 90 ₽", callback_data="uc_60")
    builder.button(text="325 UC - 450 ₽", callback_data="uc_325")
    builder.button(text="660 UC - 900 ₽", callback_data="uc_660")
    builder.button(text="1800 UC - 2300 ₽", callback_data="uc_1800")
    builder.button(text="3850 UC - 4600 ₽", callback_data="uc_3850")
    builder.button(text="8100 UC - 9200 ₽", callback_data="uc_8100")
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
        "🆔 Пожалуйста, введите ваш **Player ID** в PUBG Mobile:\n"
        "(Пример: `5123456789`)",
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseState.waiting_for_player_id)

@dp.message(PurchaseState.waiting_for_player_id)
async def process_player_id(message: types.Message, state: FSMContext):
    player_id = message.text.strip()
    data = await state.get_data()
    chosen_uc = data.get("chosen_uc")
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET player_id = ? WHERE user_id = ?", (player_id, message.from_user.id))
    conn.commit()
    conn.close()
    
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 СБП / Карты РФ", callback_data="pay_sbp")
    builder.button(text="🌏 Карты стран Азии", callback_data="pay_asia")
    builder.adjust(1)

    await message.answer(
        f"✅ **Данные успешно сохранены!**\n\n"
        f"📦 Пакет: **{chosen_uc} UC**\n"
        f"🆔 Игровой ID: `{player_id}`\n\n"
        f"💳 **Выберите удобный способ оплаты:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# ----------------- ВЫДАЧА РЕКВИЗИТОВ ОПЛАТЫ -----------------
@dp.callback_query(F.data == "pay_sbp")
async def pay_sbp(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        f"🇷🇺 **Оплата через СБП или карты РФ:**\n\n"
        f"{SBP_DETAILS}\n\n"
        f"📸 После оплаты отправьте скриншот/чек сюда и напишите администратору: {ADMIN_USERNAME}",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "pay_asia")
async def pay_asia(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        f"🌏 **Оплата картами стран Азии:**\n\n"
        f"{ASIA_DETAILS}\n\n"
        f"📸 После оплаты отправьте скриншот/чек сюда и напишите администратору: {ADMIN_USERNAME}",
        parse_mode="Markdown"
    )

# ----------------- ПРОФИЛЬ И БАЛАНС -----------------
@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT player_id, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    player_id = row[0] if row and row[0] else "Не зарегистрирован ❌"
    balance = row[1] if row and row[1] is not None else 0.0
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Пополнить баланс", callback_data="top_up")
    builder.button(text="⬅️ Назад", callback_data="back_home")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"👤 **Ваш профиль:**\n\n"
        f"🆔 Telegram ID: `{user_id}`\n"
        f"🎮 PUBG Player ID: `{player_id}`\n"
        f"💰 Баланс: **{balance} ₽**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "top_up")
async def top_up_balance(callback: types.CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 СБП / Карты РФ", callback_data="pay_sbp")
    builder.button(text="🌏 Карты стран Азии", callback_data="pay_asia")
    builder.button(text="⬅️ Назад в профиль", callback_data="profile")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "💳 **Пополнение баланса**\n\n"
        "Выберите способ оплаты для пополнения счета:",
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
    
    await callback.message.edit_text(
        "👋 **Главное меню:**\n\nПожалуйста, выберите нужный раздел:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(f"🛠 Для связи с администратором: {ADMIN_USERNAME}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
