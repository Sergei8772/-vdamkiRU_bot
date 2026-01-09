import os
import logging
from telegram.ext import Application, CommandHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.environ.get("BOT_TOKEN", "8236271877:AAHO2Eb6Lakd3gOsvQoS8PGLPTkVwbQHYMY")

async def start(update, context):
    """Простая команда старт"""
    await update.message.reply_text("✅ Бот работает на Scalingo!")

def main():
    """Минимальный запуск"""
    print("🚀 Запуск бота на Scalingo...")
    
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        
        # Добавляем только одну команду для теста
        app.add_handler(CommandHandler("start", start))
        
        print("✅ Приложение создано")
        print("🤖 Запускаю polling...")
        
        # Запускаем бота
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
