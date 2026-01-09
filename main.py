import os
import sys
import logging

print("=" * 60)
print("🤖 TELEGRAM BOT STARTING ON SCALINGO")
print("=" * 60)

# Проверяем Python версию
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

# Пытаемся импортировать
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Проверяем токен
TOKEN = os.environ.get("BOT_TOKEN", "")
print(f"Token exists: {'YES' if TOKEN else 'NO'}")

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable not set!")
    print("👉 Set it in Scalingo Dashboard → Environment")
    sys.exit(1)

async def start(update: Update, context):
    await update.message.reply_text("✅ Bot is working on Scalingo!")

def main():
    print("🚀 Creating application...")
    
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        print("✅ Application created successfully")
        print("🤖 Starting bot polling...")
        
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Runtime error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
