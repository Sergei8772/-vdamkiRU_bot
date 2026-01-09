import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения Scalingo
TOKEN = os.environ.get("BOT_TOKEN", "8236271877:AAHO2Eb6Lakd3gOsvQoS8PGLPTkVwbQHYMY")

# ========== ПРОСТАЯ ФУНКЦИОНАЛЬНОСТЬ ==========
games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Простая команда старт для теста"""
    try:
        await update.message.reply_text(
            "✅ Бот работает на Scalingo!\n"
            "Тестовое сообщение от бота."
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")

async def test_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Тест кнопок"""
    keyboard = [
        [InlineKeyboardButton("Кнопка 1", callback_data="btn1"),
         InlineKeyboardButton("Кнопка 2", callback_data="btn2")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Тест кнопок:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "btn1":
        await query.edit_message_text(text="Вы нажали кнопку 1")
    elif query.data == "btn2":
        await query.edit_message_text(text="Вы нажали кнопку 2")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Помощь"""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - запуск бота\n"
        "/test - тест кнопок\n"
        "/help - эта справка"
    )

def main() -> None:
    """ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА"""
    print("=" * 60)
    print("🚀 ЗАПУСК ТЕЛЕГРАМ БОТА НА SCALINGO")
    print("=" * 60)
    
    # Проверяем токен
    if not TOKEN:
        print("❌ ОШИБКА: Токен бота не найден!")
        print("👉 Установите переменную окружения BOT_TOKEN в Scalingo")
        return
    
    print(f"✅ Токен получен: {TOKEN[:15]}...")
    print("🔄 Создаю приложение...")
    
    try:
        # 1. Создаем приложение
        app = Application.builder().token(TOKEN).build()
        print("✅ Приложение создано")
        
        # 2. Регистрируем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("test", test_button))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CallbackQueryHandler(button_handler))
        print("✅ Обработчики зарегистрированы")
        
        # 3. Запускаем бота
        print("🤖 Запускаю бота...")
        print("=" * 60)
        
        app.run_polling(
            drop_pending_updates=True,
            timeout=30,
            poll_interval=1.0
        )
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
