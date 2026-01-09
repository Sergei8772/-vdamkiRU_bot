import logging
import os
import json
from typing import Optional, Tuple, List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TOKEN = os.environ.get("BOT_TOKEN", "8236271877:AAHO2Eb6Lakd3gOsvQoS8PGLPTkVwbQHYMY")

# Игровые константы
EMPTY = ' '
WHITE_PAWN = '⚪'
BLACK_PAWN = '⚫'
WHITE_KING = '⬜'
BLACK_KING = '⬛'

# Состояния для ConversationHandler
MENU, BOT_LEVEL, FRIEND_GAME = range(3)

# Глобальные переменные
games = {}
user_stats = {}
STATS_FILE = "user_stats.json"

class CheckersGame:
    """Класс для игры в шашки"""
    
    def __init__(self, game_type="friend", bot_level="medium"):
        self.board = [[EMPTY] * 8 for _ in range(8)]
        self.selected: Optional[Tuple[int, int]] = None
        self.current_player = "WHITE"
        self.game_active = False
        self.white_count = 12
        self.black_count = 12
        self.message_id: Optional[int] = None
        self.game_type = game_type  # "friend" или "bot"
        self.bot_level = bot_level  # "easy", "medium", "hard"
        self.last_capture_pos: Optional[Tuple[int, int]] = None
        self.must_continue_capture = False
        
        self._setup_board()
    
    def _setup_board(self) -> None:
        """Инициализация доски"""
        for i in range(8):
            self.board[i] = [EMPTY] * 8
        
        self.selected = None
        self.current_player = "WHITE"
        self.game_active = True
        self.white_count = 12
        self.black_count = 12
        self.last_capture_pos = None
        self.must_continue_capture = False
        
        # Расстановка шашек
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = BLACK_PAWN
        
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = WHITE_PAWN
    
    def check_promotion(self, row: int, col: int) -> bool:
        """Проверка превращения в дамку"""
        piece = self.board[row][col]
        if piece == WHITE_PAWN and row == 0:
            self.board[row][col] = WHITE_KING
            return True
        elif piece == BLACK_PAWN and row == 7:
            self.board[row][col] = BLACK_KING
            return True
        return False
    
    def get_possible_moves(self, row: int, col: int) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]], List[Tuple[int, int]]]]:
        """Получение возможных ходов для шашки или дамки"""
        piece = self.board[row][col]
        
        # Если поле пустое, возвращаем пустой список
        if piece == EMPTY:
            return []
        
        # Получаем все возможные ходы
        all_moves = self._get_all_moves_for_piece(row, col, piece)
        
        # Если есть обязательные взятия, фильтруем только взятия
        if self.has_any_captures():
            capture_moves = [move for move in all_moves if move[2]]  # move[2] - is_capture
            if capture_moves:
                return capture_moves
        
        return all_moves
    
    def _get_all_moves_for_piece(self, row: int, col: int, piece: str) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]], List[Tuple[int, int]]]]:
        """Получение всех возможных ходов для конкретной фигуры"""
        moves = []
        
        if piece in [WHITE_KING, BLACK_KING]:
            moves = self._get_king_moves(row, col, piece)
        else:
            moves = self._get_pawn_moves(row, col, piece)
        
        return moves
    
    def _get_king_moves(self, row: int, col: int, piece: str) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]], List[Tuple[int, int]]]]:
        """Получение ходов для дамки с любой глубиной"""
        moves = []
        is_white = piece == WHITE_KING
        enemy_pawn = BLACK_PAWN if is_white else WHITE_PAWN
        enemy_king = BLACK_KING if is_white else WHITE_KING
        enemy_pieces = [enemy_pawn, enemy_king]
        
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            capture_made = False
            captured_positions = []
            
            for step in range(1, 8):
                new_row, new_col = row + dr * step, col + dc * step
                
                if not (0 <= new_row < 8 and 0 <= new_col < 8):
                    break
                
                target = self.board[new_row][new_col]
                
                if not capture_made:
                    # Простой ход без взятия
                    if target == EMPTY:
                        moves.append((new_row, new_col, False, None, []))
                    elif target in enemy_pieces:
                        # Нашли вражескую шашку
                        land_row, land_col = new_row + dr, new_col + dc
                        if 0 <= land_row < 8 and 0 <= land_col < 8 and self.board[land_row][land_col] == EMPTY:
                            capture_made = True
                            captured_positions.append((new_row, new_col))
                            
                            # Продолжаем движение после взятия
                            for step2 in range(1, 8):
                                final_row, final_col = land_row + dr * step2, land_col + dc * step2
                                if not (0 <= final_row < 8 and 0 <= final_col < 8):
                                    break
                                
                                if self.board[final_row][final_col] == EMPTY:
                                    moves.append((final_row, final_col, True, (new_row, new_col), [(new_row, new_col)]))
                                else:
                                    break
                        else:
                            break
                    else:
                        # Своя шашка
                        break
                else:
                    # После взятия можно двигаться только через пустые клетки
                    if target == EMPTY:
                        # Добавляем ход с учетом уже съеденных шашек
                        moves.append((new_row, new_col, True, captured_positions[0], captured_positions.copy()))
                    else:
                        break
        
        return moves
    
    def _get_pawn_moves(self, row: int, col: int, piece: str) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]], List[Tuple[int, int]]]]:
        """Получение ходов для простой шашки"""
        moves = []
        is_white = piece == WHITE_PAWN
        
        if is_white:
            move_dirs = [(-1, -1), (-1, 1)]
            enemy_pieces = (BLACK_PAWN, BLACK_KING)
        else:
            move_dirs = [(1, -1), (1, 1)]
            enemy_pieces = (WHITE_PAWN, WHITE_KING)
        
        # Простые ходы
        for dr, dc in move_dirs:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if self.board[new_row][new_col] == EMPTY:
                    moves.append((new_row, new_col, False, None, []))
        
        # Взятия
        capture_dirs = [(2, -2), (2, 2), (-2, -2), (-2, 2)]
        for dr, dc in capture_dirs:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                mid_row, mid_col = (row + new_row) // 2, (col + new_col) // 2
                if (self.board[new_row][new_col] == EMPTY and 
                    self.board[mid_row][mid_col] in enemy_pieces):
                    moves.append((new_row, new_col, True, (mid_row, mid_col), [(mid_row, mid_col)]))
        
        return moves
    
    def has_any_captures(self) -> bool:
        """Проверка обязательных взятий"""
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    moves = self.get_possible_moves(row, col)
                    for _, _, is_capture, _, _ in moves:
                        if is_capture:
                            return True
        return False
    
    def get_forced_captures(self) -> List[Tuple[int, int]]:
        """Получение шашек с обязательными взятиями"""
        forced = []
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    moves = self.get_possible_moves(row, col)
                    for _, _, is_capture, _, _ in moves:
                        if is_capture:
                            forced.append((row, col))
                            break
        
        return forced
    
    def count_pieces(self) -> None:
        """Подсчет шашек"""
        self.white_count = 0
        self.black_count = 0
        
        for row in self.board:
            for cell in row:
                if cell in (WHITE_PAWN, WHITE_KING):
                    self.white_count += 1
                elif cell in (BLACK_PAWN, BLACK_KING):
                    self.black_count += 1
    
    def check_game_over(self) -> Optional[str]:
        """Проверка окончания игры"""
        self.count_pieces()
        
        if self.white_count == 0:
            return "🏆 ЧЕРНЫЕ ПОБЕДИЛИ!"
        if self.black_count == 0:
            return "🏆 БЕЛЫЕ ПОБЕДИЛИ!"
        
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        has_moves = False
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    if self.get_possible_moves(row, col):
                        has_moves = True
                        break
            if has_moves:
                break
        
        if not has_moves:
            winner = "⚫ ЧЕРНЫЕ" if self.current_player == "WHITE" else "⚪ БЕЛЫЕ"
            return f"🏆 {winner} ПОБЕДИЛИ!"
        
        return None

class UserStats:
    """Класс для статистики пользователя"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.vs_bot_wins = 0
        self.vs_bot_losses = 0
        self.vs_bot_draws = 0
        self.vs_friend_wins = 0
        self.vs_friend_losses = 0
        self.vs_friend_draws = 0
        self.total_games = 0
    
    def add_result(self, game_type: str, result: str) -> None:
        """Добавить результат игры"""
        if game_type == "bot":
            if result == "win":
                self.vs_bot_wins += 1
            elif result == "loss":
                self.vs_bot_losses += 1
            else:
                self.vs_bot_draws += 1
        else:  # friend
            if result == "win":
                self.vs_friend_wins += 1
            elif result == "loss":
                self.vs_friend_losses += 1
            else:
                self.vs_friend_draws += 1
        
        self.total_games += 1
        save_stats()
    
    def get_stats_text(self) -> str:
        """Получить текст статистики"""
        bot_total = self.vs_bot_wins + self.vs_bot_losses + self.vs_bot_draws
        friend_total = self.vs_friend_wins + self.vs_friend_losses + self.vs_friend_draws
        
        bot_win_rate = (self.vs_bot_wins / bot_total * 100) if bot_total > 0 else 0
        friend_win_rate = (self.vs_friend_wins / friend_total * 100) if friend_total > 0 else 0
        
        return f"""📊 ВАША СТАТИСТИКА:

🤖 ПРОТИВ БОТА:
• Побед: {self.vs_bot_wins}
• Поражений: {self.vs_bot_losses}
• Ничьих: {self.vs_bot_draws}
• Всего игр: {bot_total}
• Процент побед: {bot_win_rate:.1f}%

👥 ПРОТИВ ДРУГА:
• Побед: {self.vs_friend_wins}
• Поражений: {self.vs_friend_losses}
• Ничьих: {self.vs_friend_draws}
• Всего игр: {friend_total}
• Процент побед: {friend_win_rate:.1f}%

🎮 ВСЕГО ИГР: {self.total_games}"""

# Функции для работы со статистикой
def load_stats() -> None:
    """Загрузка статистики из файла"""
    global user_stats
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for user_id_str, stats_data in data.items():
                    stats = UserStats(int(user_id_str))
                    for key, value in stats_data.items():
                        setattr(stats, key, value)
                    user_stats[int(user_id_str)] = stats
    except Exception as e:
        logger.error(f"Ошибка при загрузке статистики: {e}")
        user_stats = {}

def save_stats() -> None:
    """Сохранение статистики в файл"""
    try:
        data = {}
        for user_id, stats in user_stats.items():
            data[str(user_id)] = {
                'vs_bot_wins': stats.vs_bot_wins,
                'vs_bot_losses': stats.vs_bot_losses,
                'vs_bot_draws': stats.vs_bot_draws,
                'vs_friend_wins': stats.vs_friend_wins,
                'vs_friend_losses': stats.vs_friend_losses,
                'vs_friend_draws': stats.vs_friend_draws,
                'total_games': stats.total_games
            }
        
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении статистики: {e}")

def get_user_stats(user_id: int) -> UserStats:
    """Получить статистику пользователя"""
    if user_id not in user_stats:
        user_stats[user_id] = UserStats(user_id)
    return user_stats[user_id]

# Меню
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать главное меню"""
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🤖 Играть с ботом", callback_data="play_bot")],
        [InlineKeyboardButton("👥 Играть с другом", callback_data="play_friend")],
        [InlineKeyboardButton("📖 Правила", callback_data="rules_menu")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 ДОБРО ПОЖАЛОВАТЬ В ШАШКИ!\n\nВыберите действие:",
        reply_markup=reply_markup
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик меню"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "profile":
        user_id = update.effective_user.id
        stats = get_user_stats(user_id)
        await query.edit_message_text(
            text=stats.get_stats_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
        return MENU
    
    elif data == "play_bot":
        keyboard = [
            [InlineKeyboardButton("🤖 Простой", callback_data="bot_easy")],
            [InlineKeyboardButton("🤖 Средний", callback_data="bot_medium")],
            [InlineKeyboardButton("🤖 Сложный", callback_data="bot_hard")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            text="Выберите уровень сложности бота:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return BOT_LEVEL
    
    elif data == "play_friend":
        chat_id = update.effective_chat.id
        game = CheckersGame(game_type="friend")
        games[chat_id] = game
        
        text = f"🎮 ИГРА С ДРУГОМ\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
        
        message = await query.edit_message_text(
            text=text,
            reply_markup=create_board_markup(game)
        )
        
        game.message_id = message.message_id
        return FRIEND_GAME
    
    elif data == "rules_menu":
        await query.edit_message_text(
            text=get_rules_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
        return MENU
    
    elif data == "help_menu":
        await query.edit_message_text(
            text=get_help_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]
            ])
        )
        return MENU
    
    elif data == "back_to_menu":
        return await show_menu_from_callback(update, context)
    
    return MENU

async def show_menu_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать меню из callback"""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🤖 Играть с ботом", callback_data="play_bot")],
        [InlineKeyboardButton("👥 Играть с другом", callback_data="play_friend")],
        [InlineKeyboardButton("📖 Правила", callback_data="rules_menu")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎮 ДОБРО ПОЖАЛОВАТЬ В ШАШКИ!\n\nВыберите действие:",
        reply_markup=reply_markup
    )
    return MENU

async def bot_level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора уровня бота"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_menu":
        return await show_menu_from_callback(update, context)
    
    level_map = {
        "bot_easy": "easy",
        "bot_medium": "medium",
        "bot_hard": "hard"
    }
    
    if data in level_map:
        chat_id = update.effective_chat.id
        game = CheckersGame(game_type="bot", bot_level=level_map[data])
        games[chat_id] = game
        
        text = f"🎮 ИГРА С БОТОМ ({level_map[data].capitalize()})\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
        
        message = await query.edit_message_text(
            text=text,
            reply_markup=create_board_markup(game)
        )
        
        game.message_id = message.message_id
        
        # Если бот играет белыми, делаем ход
        if game.current_player == "WHITE" and game.game_type == "bot":
            await make_bot_move(update, context, chat_id)
        
        return FRIEND_GAME
    
    return BOT_LEVEL

def create_board_markup(game: CheckersGame) -> InlineKeyboardMarkup:
    """Создание доски"""
    keyboard = []
    
    possible_moves = []
    if game.selected:
        from_row, from_col = game.selected
        possible_moves = game.get_possible_moves(from_row, from_col)
    
    moves_dict = {}
    for mr, mc, is_cap, _, _ in possible_moves:
        moves_dict[(mr, mc)] = is_cap
    
    for row in range(8):
        row_buttons = []
        for col in range(8):
            cell = game.board[row][col]
            
            if (row + col) % 2 == 0:
                btn_text = "   "
            else:
                if cell == EMPTY:
                    if (row, col) in moves_dict:
                        btn_text = " ⚔ " if moves_dict[(row, col)] else " ◦ "
                    else:
                        btn_text = "   "
                else:
                    if cell == WHITE_PAWN:
                        btn_text = " ⚪ "
                    elif cell == BLACK_PAWN:
                        btn_text = " ⚫ "
                    elif cell == WHITE_KING:
                        btn_text = " ⬜ "
                    elif cell == BLACK_KING:
                        btn_text = " ⬛ "
                    else:
                        btn_text = "   "
            
            if game.selected and game.selected == (row, col) and cell != EMPTY:
                btn_text = "🔴"
            
            button = InlineKeyboardButton(btn_text, callback_data=f"{row}_{col}")
            row_buttons.append(button)
        
        keyboard.append(row_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🤝 Ничья", callback_data="draw"),
        InlineKeyboardButton("🏳️ Сдаться", callback_data="surrender"),
        InlineKeyboardButton("📋 Меню", callback_data="game_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def update_board(update: Update, game: CheckersGame, text: str) -> None:
    """Обновление доски"""
    try:
        query = update.callback_query
        await query.edit_message_text(
            text=text,
            reply_markup=create_board_markup(game)
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить доску: {e}")
        query = update.callback_query
        message = await query.message.reply_text(
            text=text,
            reply_markup=create_board_markup(game)
        )
        game.message_id = message.message_id

async def game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик игры"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    if chat_id not in games:
        await query.edit_message_text(
            text="Игра не найдена. Вернитесь в меню.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Меню", callback_data="game_to_menu")]
            ])
        )
        return MENU
    
    game = games[chat_id]
    data = query.data
    
    if data == "game_to_menu":
        # Сохраняем результат как поражение при выходе
        if game.game_active:
            user_id = update.effective_user.id
            stats = get_user_stats(user_id)
            if game.game_type == "bot":
                stats.add_result("bot", "loss")
            else:
                stats.add_result("friend", "loss")
        
        del games[chat_id]
        return await show_menu_from_callback(update, context)
    
    if data == "draw":
        user_id = update.effective_user.id
        stats = get_user_stats(user_id)
        if game.game_type == "bot":
            stats.add_result("bot", "draw")
        else:
            stats.add_result("friend", "draw")
        
        await query.message.reply_text("🤝 Игра окончена по соглашению")
        game.game_active = False
        del games[chat_id]
        return await show_menu_from_callback(update, context)
    
    if data == "surrender":
        user_id = update.effective_user.id
        stats = get_user_stats(user_id)
        result = "loss" if game.current_player == "WHITE" else "win"
        if game.game_type == "bot":
            stats.add_result("bot", result)
        else:
            stats.add_result("friend", result)
        
        winner = "⚫ ЧЕРНЫЕ" if game.current_player == "WHITE" else "⚪ БЕЛЫЕ"
        await query.message.reply_text(f"🏳️ {winner} ПОБЕДИЛИ!")
        game.game_active = False
        del games[chat_id]
        return await show_menu_from_callback(update, context)
    
    if not game.game_active:
        await query.answer("Игра окончена")
        return FRIEND_GAME
    
    game_over = game.check_game_over()
    if game_over:
        user_id = update.effective_user.id
        stats = get_user_stats(user_id)
        
        # Определяем результат для текущего пользователя
        if "БЕЛЫЕ" in game_over:
            result = "win" if game.current_player == "BLACK" else "loss"
        else:
            result = "win" if game.current_player == "WHITE" else "loss"
        
        if game.game_type == "bot":
            stats.add_result("bot", result)
        else:
            stats.add_result("friend", result)
        
        await query.message.reply_text(f"🏁 {game_over}")
        game.game_active = False
        del games[chat_id]
        return await show_menu_from_callback(update, context)
    
    row, col = map(int, data.split('_'))
    
    if (row + col) % 2 == 0:
        return FRIEND_GAME
    
    cell = game.board[row][col]
    
    if game.selected is None:
        # Выбор шашки
        if game.current_player == "WHITE":
            if cell not in [WHITE_PAWN, WHITE_KING]:
                if cell != EMPTY:
                    await query.answer("Сейчас ходят ⚪ БЕЛЫЕ!")
                return FRIEND_GAME
        else:
            if cell not in [BLACK_PAWN, BLACK_KING]:
                if cell != EMPTY:
                    await query.answer("Сейчас ходят ⚫ ЧЕРНЫЕ!")
                return FRIEND_GAME
        
        must_capture = game.has_any_captures()
        if must_capture:
            forced_captures = game.get_forced_captures()
            if (row, col) not in forced_captures:
                await query.answer("Сначала съешьте шашку противника!", show_alert=True)
                return FRIEND_GAME
        
        game.selected = (row, col)
        text = f"Выбрана шашка\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
        await update_board(update, game, text)
    
    else:
        # Ход выбранной шашкой
        from_row, from_col = game.selected
        from_cell = game.board[from_row][from_col]
        
        moves = game.get_possible_moves(from_row, from_col)
        
        selected_move = None
        for mr, mc, is_cap, enemy_pos, captured_list in moves:
            if mr == row and mc == col:
                selected_move = (mr, mc, is_cap, enemy_pos, captured_list)
                break
        
        if not selected_move:
            # Выбор другой шашки
            if (game.current_player == "WHITE" and cell in [WHITE_PAWN, WHITE_KING]) or \
               (game.current_player == "BLACK" and cell in [BLACK_PAWN, BLACK_KING]):
                
                must_capture = game.has_any_captures()
                if must_capture:
                    forced_captures = game.get_forced_captures()
                    if (row, col) not in forced_captures:
                        await query.answer("Сначала съешьте шашку противника!", show_alert=True)
                        return FRIEND_GAME
                
                game.selected = (row, col)
                await update_board(update, game, "Выбрана новая шашка")
            else:
                await query.answer("❌ Неверный ход!", show_alert=True)
            return FRIEND_GAME
        
        move_row, move_col, is_capture, enemy_pos, captured_list = selected_move
        
        # Проверка обязательного взятия
        if not is_capture and game.has_any_captures():
            moves_for_this_piece = game.get_possible_moves(from_row, from_col)
            piece_has_captures = any(cap for _, _, cap, _, _ in moves_for_this_piece)
            
            if piece_has_captures:
                await query.answer("Вы должны съесть шашку противника!", show_alert=True)
                return FRIEND_GAME
        
        # Выполнение хода
        game.board[move_row][move_col] = from_cell
        game.board[from_row][from_col] = EMPTY
        
        # Удаление съеденных шашек
        if is_capture and captured_list:
            for enemy_row, enemy_col in captured_list:
                game.board[enemy_row][enemy_col] = EMPTY
        
        # Превращение в дамку
        game.check_promotion(move_row, move_col)
        game.count_pieces()
        
        # Проверка продолжения взятия для дамки
        if is_capture:
            moves_after = game.get_possible_moves(move_row, move_col)
            can_continue = any(cap for _, _, cap, _, _ in moves_after)
            
            if can_continue:
                game.selected = (move_row, move_col)
                msg = "Съедено! Бейте дальше!"
            else:
                game.selected = None
                game.current_player = "BLACK" if game.current_player == "WHITE" else "WHITE"
                msg = "Шашка съедена!"
        else:
            game.selected = None
            game.current_player = "BLACK" if game.current_player == "WHITE" else "WHITE"
            msg = "Ход сделан!"
        
        # Проверка окончания игры
        game_over = game.check_game_over()
        if game_over:
            user_id = update.effective_user.id
            stats = get_user_stats(user_id)
            
            if "БЕЛЫЕ" in game_over:
                result = "win" if game.current_player == "BLACK" else "loss"
            else:
                result = "win" if game.current_player == "WHITE" else "loss"
            
            if game.game_type == "bot":
                stats.add_result("bot", result)
            else:
                stats.add_result("friend", result)
            
            await query.message.reply_text(f"🏁 {game_over}")
            game.game_active = False
            del games[chat_id]
            return await show_menu_from_callback(update, context)
        
        text = f"{msg}\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
        await update_board(update, game, text)
        
        # Ход бота, если игра против бота
        if game.game_type == "bot" and game.game_active:
            await make_bot_move(update, context, chat_id)
    
    return FRIEND_GAME

async def make_bot_move(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Ход бота"""
    try:
        game = games[chat_id]
        
        # Искусственная задержка для реалистичности
        import asyncio
        await asyncio.sleep(1)
        
        # Простой AI для бота
        best_move = None
        best_score = -9999
        
        current_pieces = (BLACK_PAWN, BLACK_KING) if game.current_player == "BLACK" else (WHITE_PAWN, WHITE_KING)
        
        # Сначала ищем взятия
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and game.board[row][col] in current_pieces:
                    moves = game.get_possible_moves(row, col)
                    for mr, mc, is_cap, enemy_pos, captured_list in moves:
                        if is_cap:
                            # Оцениваем взятие
                            score = len(captured_list) * 10
                            if mr == 0 or mr == 7:  # Превращение в дамку
                                score += 5
                            if score > best_score:
                                best_score = score
                                best_move = (row, col, mr, mc, is_cap, enemy_pos, captured_list)
        
        # Если нет взятий, ищем обычные ходы
        if not best_move:
            for row in range(8):
                for col in range(8):
                    if (row + col) % 2 == 1 and game.board[row][col] in current_pieces:
                        moves = game.get_possible_moves(row, col)
                        for mr, mc, is_cap, enemy_pos, captured_list in moves:
                            if not is_cap:
                                # Оцениваем простой ход
                                score = 0
                                if game.board[row][col] in [WHITE_PAWN, BLACK_PAWN]:
                                    if game.current_player == "WHITE" and mr < row:  # Белые идут вверх
                                        score += 1
                                    elif game.current_player == "BLACK" and mr > row:  # Черные идут вниз
                                        score += 1
                                if score > best_score:
                                    best_score = score
                                    best_move = (row, col, mr, mc, is_cap, enemy_pos, captured_list)
        
        if best_move:
            from_row, from_col, to_row, to_col, is_cap, enemy_pos, captured_list = best_move
            
            # Выполняем ход
            from_cell = game.board[from_row][from_col]
            game.board[to_row][to_col] = from_cell
            game.board[from_row][from_col] = EMPTY
            
            if is_cap and captured_list:
                for enemy_row, enemy_col in captured_list:
                    game.board[enemy_row][enemy_col] = EMPTY
            
            game.check_promotion(to_row, to_col)
            game.count_pieces()
            
            # Проверка продолжения взятия
            if is_cap:
                moves_after = game.get_possible_moves(to_row, to_col)
                can_continue = any(cap for _, _, cap, _, _ in moves_after)
                
                if can_continue:
                    game.selected = (to_row, to_col)
                    msg = "Бот съел шашку! Продолжает брать..."
                else:
                    game.selected = None
                    game.current_player = "WHITE" if game.current_player == "BLACK" else "BLACK"
                    msg = "Бот сделал ход!"
            else:
                game.selected = None
                game.current_player = "WHITE" if game.current_player == "BLACK" else "BLACK"
                msg = "Бот сделал ход!"
            
            # Проверка окончания игры
            game_over = game.check_game_over()
            if game_over:
                user_id = update.effective_user.id
                stats = get_user_stats(user_id)
                
                if "БЕЛЫЕ" in game_over:
                    result = "win" if game.current_player == "BLACK" else "loss"
                else:
                    result = "win" if game.current_player == "WHITE" else "loss"
                
                stats.add_result("bot", result)
                
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=game.message_id,
                    text=f"{msg}\n{game_over}",
                    reply_markup=create_board_markup(game)
                )
                game.game_active = False
                return
            
            text = f"{msg}\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.message_id,
                text=text,
                reply_markup=create_board_markup(game)
            )
    
    except Exception as e:
        logger.error(f"Ошибка при ходе бота: {e}")

def get_rules_text() -> str:
    """Текст правил"""
    return """🎮 РУССКИЕ ШАШКИ - ПРАВИЛА

ШАШКИ:
⚪ - белая простая
⚫ - черная простая  
⬜ - белая дамка
⬛ - черная дамка

ОСНОВНЫЕ ПРАВИЛА:
1. Ходят по очереди, белые начинают
2. Ходят только по черным клеткам
3. Простые шашки ходят вперед по диагонали
4. Дамка ходит на любое расстояние по диагонали
5. Взятие обязательно, если есть возможность
6. При взятии шашка перепрыгивает через врага
7. Дамка при взятии может перепрыгивать через несколько шашек
8. Простая шашка становится дамкой, достигая последнего ряда
9. Игра до полного уничтожения шашек противника

УПРАВЛЕНИЕ:
• Выберите свою шашку
• Выберите клетку для хода
• Для дамки доступны дальние ходы

🎯 ЦЕЛЬ: Съесть все шашки противника или заблокировать их!"""

def get_help_text() -> str:
    """Текст помощи"""
    return """🎮 ПОМОЩЬ ПО БОТУ

КОМАНДЫ:
/menu - главное меню
/start - начать игру (устаревшее, используйте меню)
/rules - правила игры
/help - эта справка

ФУНКЦИИ БОТА:
1. 👤 Мой профиль - статистика игр
2. 🤖 Играть с ботом - три уровня сложности
3. 👥 Играть с другом - игра на одном устройстве

В ИГРЕ:
• 🤝 Ничья - предложить ничью
• 🏳️ Сдаться - сдаться
• 📋 Меню - вернуться в меню

ПРИМЕЧАНИЕ:
• Статистика сохраняется автоматически
• Игра против друга на одном устройстве
• Бот использует разные стратегии для каждого уровня"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    return await show_menu(update, context)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Правила игры"""
    await update.message.reply_text(get_rules_text())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Справка"""
    await update.message.reply_text(get_help_text())

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main() -> None:
    """Главная функция запуска"""
    print("=" * 50)
    print("🎮 БОТ ДЛЯ РУССКИХ ШАШЕК С МЕНЮ ЗАПУСКАЕТСЯ")
    print("=" * 50)
    
    # Загружаем статистику
    load_stats()
    print("✅ Статистика загружена")
    
    # Проверка токена
    if not TOKEN:
        print("❌ ОШИБКА: Токен бота не найден!")
        print("👉 Установите переменную окружения BOT_TOKEN")
        return
    
    print(f"✅ Токен получен")
    print("🔄 Создаю приложение...")
    
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        print("✅ Приложение создано")
        
        # Создаем ConversationHandler для меню
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start_command),
                         CommandHandler('menu', show_menu)],
            states={
                MENU: [CallbackQueryHandler(menu_handler)],
                BOT_LEVEL: [CallbackQueryHandler(bot_level_handler)],
                FRIEND_GAME: [CallbackQueryHandler(game_handler)]
            },
            fallbacks=[CommandHandler('menu', show_menu)]
        )
        
        # Регистрируем обработчики
        app.add_handler(conv_handler)
        app.add_handler(CommandHandler("rules", rules_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_error_handler(error_handler)
        print("✅ Обработчики зарегистрированы")
        
        # Запускаем бота
        print("🤖 Запускаю бота...")
        print("=" * 50)
        
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
