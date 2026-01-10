import logging
import random
import string
import asyncio

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes
)

from config import config
from database import Database
from game_logic import CheckersGame
from ai_engine import BotPlayer
from keyboard import (
    create_board_markup, create_main_menu_keyboard,
    create_new_game_keyboard, create_accept_invite_keyboard,
    create_bot_game_keyboard
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database(config.DATABASE_PATH)

# Глобальные переменные
pending_invitations = {}
bot_games = {}
friend_games = {}

def generate_game_id(length: int = 8) -> str:
    """Сгенерировать уникальный ID игры"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ==================== КОМАНДЫ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    welcome_text = """🎮 Добро пожаловать в Шашки vDAMKI!

@vdamkiRU_bot - это бот для игры в русские шашки.

ОСНОВНЫЕ ВОЗМОЖНОСТИ:
• Игра в шашки с друзьями
• Игра против ИИ
• Полноценные правила русских шашек
• Обязательное взятие
• Цепочки взятий
• Дамки с дальним ходом

Удачи за доской! 🎲"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_menu_keyboard()
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /menu"""
    await update.message.reply_text(
        "📋 Главное меню",
        reply_markup=create_main_menu_keyboard()
    )

async def bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /bot"""
    await update.message.reply_text(
        "🤖 Начать игру с ботом:",
        reply_markup=InlineKeyboardMarkup([[ 
            InlineKeyboardButton("🎮 Начать игру", callback_data="new_game"),
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /game"""
    user = update.effective_user
    chat = update.effective_chat
    
    active_games = db.get_chat_games_count(chat.id)
    if active_games >= config.MAX_GAMES_PER_CHAT:
        await update.message.reply_text(
            "⚠️ В этой группе уже слишком много активных игр."
        )
        return
    
    display_name = user.username or user.first_name or "Игрок"
    
    await update.message.reply_text(
        f"🎮 Новая игра с другом\n\nВыберите соперника:",
        reply_markup=create_new_game_keyboard(chat.id, user.id, display_name)
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats"""
    user = update.effective_user
    
    stats = db.get_user_stats(user.id)
    
    total = stats.get('games_played', 0)
    if total == 0:
        stats_text = "📊 У вас еще нет сыгранных игр.\nНачните первую игру!"
    else:
        win_rate = stats.get('win_rate', 0)
        loss_rate = stats.get('loss_rate', 0)
        draw_rate = stats.get('draw_rate', 0)
        
        stats_text = f"""📊 Ваша статистика:

🎮 Всего игр: {total}
🏆 Побед: {stats.get('games_won', 0)} ({win_rate:.1f}%)
💔 Поражений: {stats.get('games_lost', 0)} ({loss_rate:.1f}%)
🤝 Ничьих: {stats.get('games_draw', 0)} ({draw_rate:.1f}%)

⭐ Рейтинг: {stats.get('rating', 1000)}"""
    
    await update.message.reply_text(
        stats_text,
        reply_markup=create_main_menu_keyboard()
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /rules"""
    rules_text = """📖 ПРАВИЛА РУССКИХ ШАШЕК

ОСНОВНЫЕ ПРАВИЛА:
1. Ходят по очереди, белые начинают
2. Ходят только по черным клеткам
3. Простые шашки ходят вперед по диагонали
4. Дамка ходит на любое расстояние по диагонали
5. ВЗЯТИЕ ОБЯЗАТЕЛЬНО, если есть возможность
6. При взятии шашка перепрыгивает через врага
7. Можно брать несколько шашек за один ход
8. Дамка при взятии может перепрыгивать через несколько шашек
9. Простая шашка становится дамкой, достигая последнего ряда
10. Игра до полного уничтожения шашек противника

ВАЖНО:
• Если есть возможность взять шашку - вы обязаны это сделать
• Можно брать шашки назад
• Можно брать несколько шашек за одну цепочку
• После взятия проверяется, можно ли продолжить взятие

🎯 ЦЕЛЬ: Съесть все шашки противника!"""
    
    await update.message.reply_text(
        rules_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """❓ ПОМОЩЬ

КАК ИГРАТЬ:
1. Вы играете БЕЛЫМИ шашками (⚪)
2. Нажмите на свою шашку, чтобы выбрать её
3. Шашка подсветится 🔴
4. Нажмите на клетку для хода
   ◦ - обычный ход
   ⚔ - взятие шашки
5. Бот сделает ответный ход

ОБЯЗАТЕЛЬНОЕ ВЗЯТИЕ:
• Если есть возможность съесть шашку - вы должны это сделать
• Можно съесть несколько шашек за один ход
• После взятия проверяется, можно ли съесть еще

УПРАВЛЕНИЕ:
🏳️ Сдаться - закончить игру
📋 Меню - вернуться в главное меню"""
    
    await update.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /top"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, rating, games_played, games_won 
        FROM users 
        WHERE games_played > 0 
        ORDER BY rating DESC 
        LIMIT 10
    ''')
    
    top_players = cursor.fetchall()
    conn.close()
    
    if not top_players:
        text = "🏆 ТОП ИГРОКОВ\n\nПока нет игроков с сыгранными играми."
    else:
        text = "🏆 ТОП ИГРОКОВ\n\n"
        for i, (username, rating, games_played, games_won) in enumerate(top_players, 1):
            if not username:
                username = "Аноним"
            
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0
            text += f"{i}. {username}\n"
            text += f"   ⭐ Рейтинг: {rating}\n"
            text += f"   🎮 Игр: {games_played} | 🏆 Побед: {win_rate:.1f}%\n\n"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

# ==================== CALLBACK ОБРАБОТЧИКИ ====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главный обработчик callback запросов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if ':' in data:
        parts = data.split(':')
        action = parts[0]
        args = parts[1:]
    else:
        action = data
        args = []
    
    if action == 'move':
        await handle_move(query, args, context)
    elif action == 'main_menu':
        await handle_main_menu(query)
    elif action == 'new_game':
        await handle_new_game(query)
    elif action == 'new_game_friend':
        await handle_new_game_friend(query)
    elif action == 'my_stats':
        await handle_my_stats(query)
    elif action == 'top_players':
        await handle_top_players(query)
    elif action == 'rules':
        await handle_rules(query)
    elif action == 'help':
        await handle_help(query)
    elif action == 'invite':
        await handle_invite(query, args)
    elif action == 'accept':
        await handle_accept_invite(query, args, context)
    elif action == 'decline':
        await handle_decline_invite(query, args)
    elif action == 'draw':
        await handle_draw(query, args)
    elif action == 'surrender':
        await handle_surrender(query, args)
    elif action == 'bot_surrender':
        await handle_bot_surrender(query, args)
    elif action == 'random_opponent':
        await handle_random_opponent(query)

async def handle_main_menu(query):
    """Обработчик главного меню"""
    await query.edit_message_text(
        "📋 Главное меню",
        reply_markup=create_main_menu_keyboard()
    )

async def handle_new_game(query):
    """Обработчик новой игры с ботом"""
    user = query.from_user
    
    game_id = generate_game_id()
    
    bot_player = BotPlayer()
    game = bot_player.setup_game()
    
    bot_games[game_id] = bot_player
    
    game_text = f"""🎮 ИГРА ПРОТИВ БОТА

⚪ Вы (Белые)
⚫ Бот (Черные)

Ход: ⚪ Ваш ход (Белые)

ВАЖНО:
• Взятие обязательно, если есть возможность
• Можно брать несколько шашек за ход
• Можно бить назад

Удачи! 🍀"""
    
    await query.edit_message_text(
        text=game_text,
        reply_markup=create_board_markup(game, game_id)
    )

async def handle_new_game_friend(query):
    """Обработчик новой игры с другом"""
    user = query.from_user
    chat_id = query.message.chat_id
    
    active_games = db.get_chat_games_count(chat_id)
    if active_games >= config.MAX_GAMES_PER_CHAT:
        await query.edit_message_text(
            "⚠️ В этой группе уже слишком много активных игр."
        )
        return
    
    display_name = user.username or user.first_name or "Игрок"
    
    await query.edit_message_text(
        f"🎮 Новая игра с другом\n\nВыберите соперника:",
        reply_markup=create_new_game_keyboard(chat_id, user.id, display_name)
    )

async def handle_move(query, args, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик хода шашки"""
    if len(args) < 2:
        await query.answer("Ошибка хода", show_alert=True)
        return
    
    try:
        row = int(args[0])
        col = int(args[1])
        
        # Если есть game_id (третий аргумент)
        game_id = args[2] if len(args) > 2 else None
        
        if not game_id:
            await query.answer("Игра не найдена", show_alert=True)
            return
            
    except (ValueError, IndexError):
        await query.answer("Ошибка данных", show_alert=True)
        return
    
    # Проверяем, существует ли игра
    if game_id not in bot_games:
        await query.answer("Игра не найдена! Начните новую игру.", show_alert=True)
        return
    
    bot_player = bot_games[game_id]
    game = bot_player.game
    
    if not game or not game.game_active:
        await query.answer("Игра завершена! Начните новую игру.", show_alert=True)
        return
    
    # Игрок всегда играет БЕЛЫМИ
    if game.current_player != "WHITE":
        await query.answer("Сейчас ход бота! Подождите...", show_alert=True)
        return
    
    cell = game.board[row][col]
    
    # Если шашка еще не выбрана
    if game.selected is None:
        # Проверяем, что это белая шашка игрока
        if cell not in ['⚪', '⬜']:
            if cell != ' ':
                await query.answer("Это не ваша шашка! Вы играете белыми (⚪).", show_alert=True)
            return
        
        # Проверяем обязательные взятия
        if game.has_any_captures():
            forced_captures = game.get_forced_captures()
            if (row, col) not in forced_captures:
                await query.answer("Вы должны съесть шашку противника!", show_alert=True)
                return
        
        # Выбираем шашку
        game.selected = (row, col)
        
        # Обновляем сообщение
        game_text = f"""🎮 Ваш ход

Выбрана шашка на ({row}, {col}).
Выберите клетку для хода."""
        
        await query.edit_message_text(
            text=game_text,
            reply_markup=create_board_markup(game, game_id)
        )
    
    else:
        # Если шашка уже выбрана, делаем ход
        from_row, from_col = game.selected
        game.selected = None
        
        success, message = bot_player.make_player_move(from_row, from_col, row, col)
        
        if success:
            # Проверяем, не закончилась ли игра
            game_over = bot_player.check_game_over()
            
            if game_over:
                if "БЕЛЫЕ" in game_over:
                    result_text = "🏆 Вы победили!"
                    db.update_user_stats(query.from_user.id, "WIN")
                elif "ЧЕРНЫЕ" in game_over:
                    result_text = "💔 Бот победил!"
                    db.update_user_stats(query.from_user.id, "LOSS")
                else:
                    result_text = "🤝 Ничья!"
                    db.update_user_stats(query.from_user.id, "DRAW")
                
                final_text = f"""🏁 ИГРА ОКОНЧЕНА!

{game_over}

{result_text}

Спасибо за игру! 🎉"""
                
                await query.edit_message_text(
                    text=final_text,
                    reply_markup=create_bot_game_keyboard(game_id)
                )
                
                if game_id in bot_games:
                    del bot_games[game_id]
                return
            
            # Если взятие продолжается, не передаем ход боту
            if game.must_capture:
                # Продолжаем взятие
                game_text = f"""🎮 Продолжайте взятие!

{message}

Выберите следующую клетку для взятия."""
                
                await query.edit_message_text(
                    text=game_text,
                    reply_markup=create_board_markup(game, game_id)
                )
                return
            
            # Показываем, что ход сделан
            await query.edit_message_text(
                text=f"✅ {message}\n\n🤖 Бот думает...",
                reply_markup=create_board_markup(game, game_id)
            )
            
            # Добавляем небольшую паузу для визуальной обратной связи
            await asyncio.sleep(0.5)
            
            # Бот делает ход
            bot_success, bot_message = bot_player.make_bot_move()
            
            if bot_success:
                # Проверяем, не закончилась ли игра после хода бота
                game_over = bot_player.check_game_over()
                
                if game_over:
                    if "БЕЛЫЕ" in game_over:
                        result_text = "🏆 Вы победили!"
                        db.update_user_stats(query.from_user.id, "WIN")
                    elif "ЧЕРНЫЕ" in game_over:
                        result_text = "💔 Бот победил!"
                        db.update_user_stats(query.from_user.id, "LOSS")
                    else:
                        result_text = "🤝 Ничья!"
                        db.update_user_stats(query.from_user.id, "DRAW")
                    
                    final_text = f"""🏁 ИГРА ОКОНЧЕНА!

{game_over}

{result_text}

Спасибо за игру! 🎉"""
                    
                    await query.edit_message_text(
                        text=final_text,
                        reply_markup=create_bot_game_keyboard(game_id)
                    )
                    
                    if game_id in bot_games:
                        del bot_games[game_id]
                    return
                
                # Продолжаем игру
                game_text = f"""🤖 Ход бота: {bot_message}

Ход: ⚪ Ваш ход (Белые)"""
                
                await query.edit_message_text(
                    text=game_text,
                    reply_markup=create_board_markup(game, game_id)
                )
            else:
                await query.answer(f"Ошибка бота: {bot_message}", show_alert=True)
        else:
            await query.answer(message, show_alert=True)

async def handle_my_stats(query):
    """Обработчик статистики"""
    user = query.from_user
    
    stats = db.get_user_stats(user.id)
    
    total = stats.get('games_played', 0)
    if total == 0:
        stats_text = "📊 У вас еще нет сыгранных игр.\nНачните первую игру!"
    else:
        win_rate = stats.get('win_rate', 0)
        loss_rate = stats.get('loss_rate', 0)
        draw_rate = stats.get('draw_rate', 0)
        
        stats_text = f"""📊 Ваша статистика:

🎮 Всего игр: {total}
🏆 Побед: {stats.get('games_won', 0)} ({win_rate:.1f}%)
💔 Поражений: {stats.get('games_lost', 0)} ({loss_rate:.1f}%)
🤝 Ничьих: {stats.get('games_draw', 0)} ({draw_rate:.1f}%)

⭐ Рейтинг: {stats.get('rating', 1000)}"""
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def handle_top_players(query):
    """Обработчик топа игроков"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, rating, games_played, games_won 
        FROM users 
        WHERE games_played > 0 
        ORDER BY rating DESC 
        LIMIT 10
    ''')
    
    top_players = cursor.fetchall()
    conn.close()
    
    if not top_players:
        text = "🏆 ТОП ИГРОКОВ\n\nПока нет игроков с сыгранными играми."
    else:
        text = "🏆 ТОП ИГРОКОВ\n\n"
        for i, (username, rating, games_played, games_won) in enumerate(top_players, 1):
            if not username:
                username = "Аноним"
            
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0
            text += f"{i}. {username}\n"
            text += f"   ⭐ Рейтинг: {rating}\n"
            text += f"   🎮 Игр: {games_played} | 🏆 Побед: {win_rate:.1f}%\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def handle_rules(query):
    """Обработчик правил"""
    rules_text = """📖 ПРАВИЛА РУССКИХ ШАШЕК

ОСНОВНЫЕ ПРАВИЛА:
1. Ходят по очереди, белые начинают
2. Ходят только по черным клеткам
3. Простые шашки ходят вперед по диагонали
4. Дамка ходит на любое расстояние по диагонали
5. ВЗЯТИЕ ОБЯЗАТЕЛЬНО, если есть возможность
6. При взятии шашка перепрыгивает через врага
7. Можно брать несколько шашек за один ход
8. Дамка при взятии может перепрыгивать через несколько шашек
9. Простая шашка становится дамкой, достигая последнего ряда
10. Игра до полного уничтожения шашек противника

ВАЖНО:
• Если есть возможность взять шашку - вы обязаны это сделать
• Можно брать шашки назад
• Можно брать несколько шашек за одну цепочку
• После взятия проверяется, можно ли продолжить взятие

🎯 ЦЕЛЬ: Съесть все шашки противника!"""
    
    await query.edit_message_text(
        rules_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def handle_help(query):
    """Обработчик помощи"""
    help_text = """❓ ПОМОЩЬ

КАК ИГРАТЬ:
1. Вы играете БЕЛЫМИ шашками (⚪)
2. Нажмите на свою шашку, чтобы выбрать её
3. Шашка подсветится 🔴
4. Нажмите на клетку для хода
   ◦ - обычный ход
   ⚔ - взятие шашки
5. Бот сделает ответный ход

ОБЯЗАТЕЛЬНОЕ ВЗЯТИЕ:
• Если есть возможность съесть шашку - вы должны это сделать
• Можно съесть несколько шашек за один ход
• После взятия проверяется, можно ли съесть еще

УПРАВЛЕНИЕ:
🏳️ Сдаться - закончить игру
📋 Меню - вернуться в главное меню"""
    
    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
    )

async def handle_invite(query, args):
    """Обработчик приглашения"""
    if len(args) < 2:
        await query.answer("Ошибка приглашения", show_alert=True)
        return
    
    invited_user_id = int(args[0])
    invited_username = args[1]
    user = query.from_user
    
    if user.id == invited_user_id:
        await query.answer("Вы не можете играть с самим собой!", show_alert=True)
        return
    
    await query.edit_message_text(
        f"✅ Приглашение отправлено пользователю @{invited_username}!"
    )

async def handle_accept_invite(query, args, context):
    """Обработчик принятия приглашения"""
    await query.edit_message_text("✅ Вы приняли приглашение!")

async def handle_decline_invite(query, args):
    """Обработчик отклонения приглашения"""
    await query.edit_message_text("❌ Вы отклонили приглашение.")

async def handle_draw(query, args):
    """Обработчик ничьей"""
    await query.answer("Функция ничьей в разработке", show_alert=True)

async def handle_surrender(query, args):
    """Обработчик сдачи"""
    await query.answer("Функция сдачи в разработке", show_alert=True)

async def handle_bot_surrender(query, args):
    """Обработчик сдачи в игре с ботом"""
    if len(args) < 1:
        await query.answer("Ошибка", show_alert=True)
        return
    
    game_id = args[0]
    user = query.from_user
    
    if game_id in bot_games:
        db.update_user_stats(user.id, "LOSS")
        del bot_games[game_id]
    
    await query.edit_message_text(
        text="🏳️ Вы сдались! Бот победил.\n\nСпасибо за игру! 🎉",
        reply_markup=create_main_menu_keyboard()
    )

async def handle_random_opponent(query):
    """Обработчик случайного соперника"""
    await query.answer(
        "Функция случайного соперника в разработке.",
        show_alert=True
    )

# ==================== ОБРАБОТЧИК ОШИБОК ====================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception: {context.error}", exc_info=True)

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def main() -> None:
    """Главная функция запуска бота"""
    print("=" * 50)
    print(f"🎮 ЗАПУСК БОТА: {config.BOT_NAME}")
    print("=" * 50)
    
    try:
        application = Application.builder().token(config.TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CommandHandler("game", game_command))
        application.add_handler(CommandHandler("bot", bot_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("rules", rules_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("top", top_command))
        
        application.add_handler(CallbackQueryHandler(callback_handler))
        
        application.add_error_handler(error_handler)
        
        print("✅ Бот запущен!")
        print("=" * 50)
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()