from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from game_logic import CheckersGame

def create_board_markup(game: CheckersGame, game_id: str = None) -> InlineKeyboardMarkup:
    """Создание клавиатуры доски"""
    keyboard = []
    
    # Получаем возможные ходы для выбранной шашки
    possible_moves = []
    moves_dict = {}
    
    if game.selected:
        from_row, from_col = game.selected
        possible_moves = game.get_possible_moves(from_row, from_col)
        
        # Создаем словарь для быстрой проверки
        for mr, mc, is_cap, _, _ in possible_moves:
            moves_dict[(mr, mc)] = is_cap
    
    for row in range(8):
        row_buttons = []
        for col in range(8):
            cell = game.board[row][col]
            btn_text = "   "  # По умолчанию пустая
            
            # Черные клетки (игровые)
            if (row + col) % 2 == 1:
                if cell != ' ':
                    # Клетка с шашкой
                    if cell == '⚪':
                        btn_text = " ⚪ "
                    elif cell == '⚫':
                        btn_text = " ⚫ "
                    elif cell == '⬜':
                        btn_text = " ⬜ "
                    elif cell == '⬛':
                        btn_text = " ⬛ "
                else:
                    # Пустая клетка - проверяем возможные ходы
                    if (row, col) in moves_dict:
                        btn_text = " ⚔ " if moves_dict[(row, col)] else " ◦ "
            
            # ПОДСВЕТКА ВЫБРАННОЙ ШАШКИ - ТОЛЬКО КРАСНЫЙ КРУЖОК
            if game.selected and game.selected == (row, col) and cell != ' ':
                btn_text = " 🔴 "
            
            # Создаем callback_data
            callback_data = f"move:{row}:{col}"
            if game_id:
                callback_data += f":{game_id}"
            
            button = InlineKeyboardButton(btn_text, callback_data=callback_data)
            row_buttons.append(button)
        
        keyboard.append(row_buttons)
    
    # Кнопки управления
    control_buttons = []
    if game.game_active:
        control_buttons = [
            InlineKeyboardButton("🤝 Ничья", callback_data=f"draw:{game_id}"),
            InlineKeyboardButton("🏳️ Сдаться", callback_data=f"surrender:{game_id}"),
            InlineKeyboardButton("📋 Меню", callback_data="main_menu")
        ]
    else:
        control_buttons = [
            InlineKeyboardButton("🔄 Новая игра", callback_data="new_game"),
            InlineKeyboardButton("📋 Меню", callback_data="main_menu")
        ]
    
    keyboard.append(control_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Создать главное меню"""
    keyboard = [
        [InlineKeyboardButton("🎮 Новая игра с другом", callback_data="new_game_friend")],
        [InlineKeyboardButton("🤖 Играть с ботом", callback_data="new_game")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton("🏆 Топ игроков", callback_data="top_players")],
        [InlineKeyboardButton("📖 Правила", callback_data="rules")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_new_game_keyboard(chat_id: int, user_id: int, username: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру для новой игры с другом"""
    keyboard = [
        [InlineKeyboardButton(f"🤝 Играть с {username}", 
                             callback_data=f"invite:{user_id}:{username}")],
        [InlineKeyboardButton("🎲 Случайный соперник", 
                             callback_data="random_opponent")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_accept_invite_keyboard(inviter_id: int, inviter_name: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру для принятия приглашения"""
    keyboard = [
        [InlineKeyboardButton(f"✅ Принять вызов от {inviter_name}", 
                             callback_data=f"accept:{inviter_id}")],
        [InlineKeyboardButton("❌ Отклонить", 
                             callback_data=f"decline:{inviter_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_bot_game_keyboard(game_id: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру для игры с ботом"""
    keyboard = [
        [InlineKeyboardButton("🏳️ Сдаться", callback_data=f"bot_surrender:{game_id}")],
        [InlineKeyboardButton("🔄 Новая игра", callback_data="new_game")],
        [InlineKeyboardButton("📋 Меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)