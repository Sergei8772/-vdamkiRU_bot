import logging
import random
import string
import asyncio
import time

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
pending_invitations = {}  # Для хранения приглашений
bot_games = {}
friend_games = {}

# Статистика производительности
performance_stats = {
    'total_games': 0,
    'avg_move_time': 0,
    'bot_thinking_time': 0
}

def generate_game_id(length: int = 8) -> str:
    """Сгенерировать уникальный ID игры"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_invitation_id(length: int = 10) -> str:
    """Сгенерировать уникальный ID приглашения"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /status (статистика бота)"""
    active_bot_games = len(bot_games)
    active_friend_games = len(friend_games)
    
    status_text = f"""📊 СТАТИСТИКА БОТА:

Активных игр с ботом: {active_bot_games}
Активных игр с друзьями: {active_friend_games}
Всего игр сыграно: {performance_stats['total_games']}
Среднее время хода: {performance_stats['avg_move_time']:.2f} сек
Среднее время ИИ: {performance_stats['bot_thinking_time']:.2f} сек

Использование памяти:
• Ожидающие приглашения: {len(pending_invitations)}"""
    
    await update.message.reply_text(
        status_text,
        reply_markup=create_main_menu_keyboard()
    )

# ==================== CALLBACK ОБРАБОТЧИКИ ====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главный обработчик callback запросов"""
    query = update.callback_query
    
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
        await handle_invite(query, args, context)
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
    elif action == 'status':
        await handle_status(query)

async def handle_main_menu(query):
    """Обработчик главного меню"""
    await query.answer()
    await query.edit_message_text(
        "📋 Главное меню",
        reply_markup=create_main_menu_keyboard()
    )

async def handle_new_game(query):
    """Обработчик новой игры с ботом"""
    await query.answer()
    user = query.from_user
    
    game_id = generate_game_id()
    
    bot_player = BotPlayer()
    game = bot_player.setup_game()
    
    bot_games[game_id] = bot_player
    performance_stats['total_games'] += 1
    
    # Очищаем старые игры при необходимости
    if len(bot_games) > 50:
        # Удаляем старые игры (первые 10)
        old_keys = list(bot_games.keys())[:10]
        for key in old_keys:
            if key in bot_games:
                del bot_games[key]
    
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
    await query.answer()
    user = query.from_user
    chat_id = query.message.chat_id
    
    active_games = db.get_chat_games_count(chat_id)
    if active_games >= config.MAX_GAMES_PER_CHAT:
        await query.edit_message_text(
            "⚠️ В этой группе уже слишком много активных игр."
        )
        return
    
    display_name = user.username or user.first_name or "Игрок"
    
    # Создаем клавиатуру с опцией приглашения друга
    keyboard = [
        [InlineKeyboardButton("👤 Пригласить друга из контактов", 
                             callback_data=f"invite:contacts:{user.id}:{display_name}")],
        [InlineKeyboardButton(f"🤝 Играть с {display_name}", 
                             callback_data=f"invite:{user.id}:{display_name}")],
        [InlineKeyboardButton("🎲 Случайный соперник", 
                             callback_data="random_opponent")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        f"🎮 Новая игра с другом\n\nВыберите способ игры:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_invite(query, args, context):
    """Обработчик приглашения друга"""
    if len(args) < 2:
        await query.answer("Ошибка приглашения", show_alert=True)
        return
    
    # Если это приглашение из контактов
    if args[0] == "contacts":
        if len(args) < 3:
            await query.answer("Ошибка приглашения", show_alert=True)
            return
        
        user_id = int(args[1])
        user_name = args[2]
        user = query.from_user
        
        # Отправляем сообщение о необходимости поделиться контактом
        invite_text = f"""👤 Пригласить друга

Чтобы пригласить друга в шашки:

1. Нажмите на кнопку "Поделиться контактом" ниже
2. Выберите друга из ваших контактов
3. Ваш друг получит приглашение

Или скопируйте ссылку на бота и отправьте другу:
https://t.me/{context.bot.username}?start=invite_{user.id}

После того как друг запустит бота командой /start, он сможет принять ваше приглашение."""
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📱 Поделиться контактом", 
                               switch_inline_query=f"@{(context.bot.username or 'vdamkiRU_bot').replace('@', '')}")
        ], [
            InlineKeyboardButton("⬅️ Назад", callback_data="new_game_friend")
        ]])
        
        await query.answer()  # Убираем часики
        await query.edit_message_text(
            text=invite_text,
            reply_markup=keyboard
        )
        return
    
    # Старое поведение для совместимости
    try:
        invited_user_id = int(args[0])
        invited_username = args[1]
        user = query.from_user
        chat_id = query.message.chat_id
        
        if user.id == invited_user_id:
            await query.answer("Вы не можете играть с самим собой!", show_alert=True)
            return
        
        # Создаем приглашение
        invitation_id = generate_invitation_id()
        
        pending_invitations[invitation_id] = {
            'from_user_id': user.id,
            'from_user_name': user.username or user.first_name,
            'to_user_id': invited_user_id,
            'to_user_name': invited_username,
            'chat_id': chat_id,
            'created_at': time.time()
        }
        
        # Очищаем старые приглашения (старше 5 минут)
        current_time = time.time()
        expired_invitations = []
        for inv_id, inv_data in pending_invitations.items():
            if current_time - inv_data['created_at'] > 300:
                expired_invitations.append(inv_id)
        
        for inv_id in expired_invitations:
            if inv_id in pending_invitations:
                del pending_invitations[inv_id]
        
        # Пытаемся отправить сообщение приглашенному пользователю
        try:
            # Создаем клавиатуру для принятия приглашения
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Принять вызов", callback_data=f"accept:{invitation_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"decline:{invitation_id}")
            ]])
            
            inviter_name = user.username or user.first_name or "Игрок"
            invite_text = f"""🎮 ПРИГЛАШЕНИЕ В ШАШКИ

{inviter_name} приглашает вас сыграть в шашки!

Принять вызов?"""
            
            # Отправляем сообщение приглашенному пользователю
            await context.bot.send_message(
                chat_id=invited_user_id,
                text=invite_text,
                reply_markup=keyboard
            )
            
            await query.answer(f"✅ Приглашение отправлено пользователю @{invited_username}!", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error sending invitation: {e}")
            await query.answer(f"Не удалось отправить приглашение. Убедитесь, что пользователь @{invited_username} запустил бота командой /start.", show_alert=True)
        
        await query.edit_message_text(
            f"✅ Приглашение отправлено пользователю @{invited_username}!"
        )
        
    except Exception as e:
        logger.error(f"Error in handle_invite: {e}")
        await query.answer("Ошибка при отправке приглашения", show_alert=True)

async def handle_accept_invite(query, args, context):
    """Обработчик принятия приглашения"""
    if len(args) < 1:
        await query.answer("Ошибка приглашения", show_alert=True)
        return
    
    invitation_id = args[0]
    user = query.from_user
    
    if invitation_id not in pending_invitations:
        await query.answer("Приглашение не найдено или устарело!", show_alert=True)
        return
    
    invitation = pending_invitations[invitation_id]
    
    # Проверяем, что приглашение предназначено этому пользователю
    if invitation['to_user_id'] != user.id:
        await query.answer("Это приглашение не для вас!", show_alert=True)
        return
    
    # Удаляем приглашение
    del pending_invitations[invitation_id]
    
    # Начинаем новую игру с ботом для принявшего приглашение
    # (пока что играем с ботом, в будущем можно добавить игру между пользователями)
    game_id = generate_game_id()
    
    bot_player = BotPlayer()
    game = bot_player.setup_game()
    
    bot_games[game_id] = bot_player
    performance_stats['total_games'] += 1
    
    inviter_name = invitation['from_user_name']
    
    game_text = f"""🎮 ИГРА ПРОТИВ БОТА

Вы приняли приглашение от {inviter_name}!

⚪ Вы (Белые)
⚫ Бот (Черные)

Ход: ⚪ Ваш ход (Белые)

ВАЖНО:
• Взятие обязательно, если есть возможность
• Можно брать несколько шашек за ход
• Можно бить назад

Удачи! 🍀"""
    
    await query.answer()  # Убираем часики
    await query.edit_message_text(
        text=game_text,
        reply_markup=create_board_markup(game, game_id)
    )
    
    # Уведомляем пригласившего
    try:
        await context.bot.send_message(
            chat_id=invitation['from_user_id'],
            text=f"✅ {user.username or user.first_name} принял(а) ваше приглашение и начал(а) игру с ботом!"
        )
    except:
        pass

async def handle_decline_invite(query, args):
    """Обработчик отклонения приглашения"""
    if len(args) < 1:
        await query.answer("Ошибка приглашения", show_alert=True)
        return
    
    invitation_id = args[0]
    user = query.from_user
    
    if invitation_id not in pending_invitations:
        await query.answer("Приглашение не найдено или устарело!", show_alert=True)
        return
    
    invitation = pending_invitations[invitation_id]
    
    # Проверяем, что приглашение предназначено этому пользователю
    if invitation['to_user_id'] != user.id:
        await query.answer("Это приглашение не для вас!", show_alert=True)
        return
    
    # Удаляем приглашение
    del pending_invitations[invitation_id]
    
    # Уведомляем пригласившего
    try:
        await query.bot.send_message(
            chat_id=invitation['from_user_id'],
            text=f"❌ {user.username or user.first_name} отклонил(а) ваше приглашение в шашки."
        )
    except:
        pass
    
    await query.answer()
    await query.edit_message_text("❌ Вы отклонили приглашение.")

async def handle_move(query, args, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик хода шашки с попап-уведомлениями"""
    start_time = time.time()
    
    if len(args) < 2:
        return
    
    try:
        row = int(args[0])
        col = int(args[1])
        
        # Если есть game_id (третий аргумент)
        game_id = args[2] if len(args) > 2 else None
        
        if not game_id:
            return
            
    except (ValueError, IndexError):
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
            else:
                await query.answer()  # Просто убираем часики для пустой клетки
            return
        
        # Проверяем обязательные взятия
        if game.has_any_captures():
            # Получаем все шашки с обязательными взятиями
            forced_captures = game.get_forced_captures()
            
            # Проверяем, есть ли у выбранной шашки взятия
            if (row, col) not in forced_captures:
                # ПОПАП-УВЕДОМЛЕНИЕ ОБ ОБЯЗАТЕЛЬНОМ ВЗЯТИИ
                await query.answer(
                    "⚠️ ОБЯЗАТЕЛЬНОЕ ВЗЯТИЕ!\n\n"
                    "Вы должны съесть шашку противника.\n\n"
                    "Эта шашка не может совершить взятие.\n"
                    "Выберите другую свою шашку, которая может съесть.\n\n"
                    "[OK]",
                    show_alert=True
                )
                return
        
        # Выбираем шашку
        game.selected = (row, col)
        
        # Обновляем сообщение
        game_text = f"""🎮 Ваш ход

Выбрана шашка на ({row}, {col}).
Выберите клетку для хода."""
        
        await query.answer()  # Убираем часики
        await query.edit_message_text(
            text=game_text,
            reply_markup=create_board_markup(game, game_id)
        )
    
    else:
        # Если шашка уже выбрана
        from_row, from_col = game.selected
        
        # Если кликнули на другую белую шашку - меняем выбор
        if cell in ['⚪', '⬜'] and (row != from_row or col != from_col):
            # Проверяем, что это белая шашка игрока
            if cell not in ['⚪', '⬜']:
                return
            
            # Проверяем обязательные взятия
            if game.has_any_captures():
                # Получаем все шашки с обязательными взятиями
                forced_captures = game.get_forced_captures()
                
                # Проверяем, есть ли у новой шашки взятия
                if (row, col) not in forced_captures:
                    # ПОПАП-УВЕДОМЛЕНИЕ ОБ ОБЯЗАТЕЛЬНОМ ВЗЯТИИ
                    await query.answer(
                        "⚠️ ОБЯЗАТЕЛЬНОЕ ВЗЯТИЕ!\n\n"
                        "Вы должны съесть шашку противника.\n\n"
                        "Эта шашка не может совершить взятие.\n"
                        "Выберите другую свою шашку, которая может съесть.\n\n"
                        "[OK]",
                        show_alert=True
                    )
                    return
            
            # Меняем выбор на новую шашку
            game.selected = (row, col)
            
            # Обновляем сообщение
            game_text = f"""🎮 Изменен выбор

Теперь выбрана шашка на ({row}, {col}).
Выберите клетку для хода."""
            
            await query.answer()  # Убираем часики
            await query.edit_message_text(
                text=game_text,
                reply_markup=create_board_markup(game, game_id)
            )
            return
        
        # Если кликнули на ту же шашку - снимаем выбор
        if cell in ['⚪', '⬜'] and row == from_row and col == from_col:
            game.selected = None
            
            # Обновляем сообщение
            game_text = """🎮 Ваш ход

Выбор шашки отменен.
Выберите шашку для хода."""
            
            await query.answer()  # Убираем часики
            await query.edit_message_text(
                text=game_text,
                reply_markup=create_board_markup(game, game_id)
            )
            return
        
        # Если кликнули на пустую клетку - пытаемся сделать ход
        # Получаем все возможные ходы для выбранной шашки
        possible_moves = game.get_possible_moves(from_row, from_col)
        
        # Ищем выбранный ход среди возможных
        selected_move = None
        for mr, mc, is_capture, _, _ in possible_moves:
            if mr == row and mc == col:
                selected_move = (mr, mc, is_capture)
                break
        
        if not selected_move:
            await query.answer("Неверный ход! Выберите другую клетку.", show_alert=True)
            return
        
        # Проверяем обязательные взятия
        if game.has_any_captures():
            _, _, is_capture_move = selected_move
            if not is_capture_move:
                # ПОПАП-УВЕДОМЛЕНИЕ: Игрок пытается сделать обычный ход вместо взятия
                await query.answer(
                    "⚠️ ОБЯЗАТЕЛЬНОЕ ВЗЯТИЕ!\n\n"
                    "Вы должны съесть шашку противника.\n\n"
                    "Вы не можете сделать обычный ход, когда есть возможность взятия.\n"
                    "Выберите клетку для взятия шашки противника.\n\n"
                    "[OK]",
                    show_alert=True
                )
                return
        
        # Делаем ход
        success, message = bot_player.make_player_move(from_row, from_col, row, col)
        
        if success:
            # Обновляем статистику времени
            move_time = time.time() - start_time
            if performance_stats['avg_move_time'] == 0:
                performance_stats['avg_move_time'] = move_time
            else:
                performance_stats['avg_move_time'] = 0.9 * performance_stats['avg_move_time'] + 0.1 * move_time
            
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
                
                await query.answer()  # Убираем часики
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
                game_text = f"""🎯 Продолжайте взятие!

{message}

Выберите следующую клетку для взятия."""
                
                await query.answer()  # Убираем часики
                await query.edit_message_text(
                    text=game_text,
                    reply_markup=create_board_markup(game, game_id)
                )
                return
            
            # Показываем, что ход сделан
            await query.answer()  # Убираем часики
            await query.edit_message_text(
                text=f"✅ {message}\n\n🤖 Бот думает...",
                reply_markup=create_board_markup(game, game_id)
            )
            
            # Добавляем небольшую паузу для визуальной обратной связи
            await asyncio.sleep(0.5)
            
            # Бот делает ход
            bot_start_time = time.time()
            bot_success, bot_message = bot_player.make_bot_move()
            bot_time = time.time() - bot_start_time
            
            # Обновляем статистику времени ИИ
            if performance_stats['bot_thinking_time'] == 0:
                performance_stats['bot_thinking_time'] = bot_time
            else:
                performance_stats['bot_thinking_time'] = 0.9 * performance_stats['bot_thinking_time'] + 0.1 * bot_time
            
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
                    
                    await query.answer()  # Убираем часики
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
                
                await query.answer()  # Убираем часики
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
    await query.answer()
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
    await query.answer()
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
    await query.answer()
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
    await query.answer()
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
    
    await query.answer()
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

async def handle_status(query):
    """Обработчик статистики бота"""
    await query.answer()
    active_bot_games = len(bot_games)
    active_friend_games = len(friend_games)
    
    status_text = f"""📊 СТАТИСТИКА БОТА:

Активных игр с ботом: {active_bot_games}
Активных игр с друзьями: {active_friend_games}
Всего игр сыграно: {performance_stats['total_games']}
Среднее время хода: {performance_stats['avg_move_time']:.2f} сек
Среднее время ИИ: {performance_stats['bot_thinking_time']:.2f} сек

Использование памяти:
• Ожидающие приглашения: {len(pending_invitations)}"""
    
    await query.edit_message_text(
        status_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        ]])
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
        application.add_handler(CommandHandler("status", status_command))
        
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