import logging
import os
from typing import Optional, Tuple, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения (для Scalingo)
TOKEN = os.environ.get("BOT_TOKEN", "8236271877:AAHO2Eb6Lakd3gOsvQoS8PGLPTkVwbQHYMY")

# Игровые константы
EMPTY = ' '
WHITE_PAWN = '⚪'
BLACK_PAWN = '⚫'
WHITE_KING = '⬜'
BLACK_KING = '⬛'

# Глобальные переменные игры
games = {}

class CheckersGame:
    """Оптимизированный класс для игры в шашки"""
    
    def __init__(self):
        self.board = [[EMPTY] * 8 for _ in range(8)]
        self.selected: Optional[Tuple[int, int]] = None
        self.current_player = "WHITE"
        self.game_active = False
        self.white_count = 12
        self.black_count = 12
        self.message_id: Optional[int] = None
        
        self._setup_board()
    
    def _setup_board(self) -> None:
        """Быстрая инициализация доски"""
        for i in range(8):
            self.board[i] = [EMPTY] * 8
        
        self.selected = None
        self.current_player = "WHITE"
        self.game_active = True
        self.white_count = 12
        self.black_count = 12
        
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
        """Быстрая проверка превращения"""
        piece = self.board[row][col]
        if piece == WHITE_PAWN and row == 0:
            self.board[row][col] = WHITE_KING
            return True
        elif piece == BLACK_PAWN and row == 7:
            self.board[row][col] = BLACK_KING
            return True
        return False
    
    def get_possible_moves(self, row: int, col: int) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]]]]:
        """Оптимизированное получение ходов"""
        moves = []
        piece = self.board[row][col]
        
        if piece in [WHITE_KING, BLACK_KING]:
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            is_white = piece == WHITE_KING
            
            for dr, dc in directions:
                for step in range(1, 8):
                    new_row, new_col = row + dr * step, col + dc * step
                    if not (0 <= new_row < 8 and 0 <= new_col < 8):
                        break
                    
                    target = self.board[new_row][new_col]
                    if target == EMPTY:
                        moves.append((new_row, new_col, False, None))
                    else:
                        enemy = (BLACK_PAWN, BLACK_KING) if is_white else (WHITE_PAWN, WHITE_KING)
                        if target in enemy:
                            land_row, land_col = new_row + dr, new_col + dc
                            if 0 <= land_row < 8 and 0 <= land_col < 8 and self.board[land_row][land_col] == EMPTY:
                                moves.append((land_row, land_col, True, (new_row, new_col)))
                        break
        else:
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
                        moves.append((new_row, new_col, False, None))
            
            # Взятия
            capture_dirs = [(2, -2), (2, 2), (-2, -2), (-2, 2)]
            for dr, dc in capture_dirs:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    mid_row, mid_col = (row + new_row) // 2, (col + new_col) // 2
                    if (self.board[new_row][new_col] == EMPTY and 
                        self.board[mid_row][mid_col] in enemy_pieces):
                        moves.append((new_row, new_col, True, (mid_row, mid_col)))
        
        return moves
    
    def has_any_captures(self) -> bool:
        """Быстрая проверка обязательных взятий"""
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    moves = self.get_possible_moves(row, col)
                    for _, _, is_capture, _ in moves:
                        if is_capture:
                            return True
        return False
    
    def get_forced_captures(self) -> List[Tuple[int, int]]:
        """Быстрое получение шашек с обязательными взятиями"""
        forced = []
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    moves = self.get_possible_moves(row, col)
                    for _, _, is_capture, _ in moves:
                        if is_capture:
                            forced.append((row, col))
                            break
        
        return forced
    
    def count_pieces(self) -> None:
        """Быстрый подсчет шашек"""
        self.white_count = 0
        self.black_count = 0
        
        for row in self.board:
            for cell in row:
                if cell in (WHITE_PAWN, WHITE_KING):
                    self.white_count += 1
                elif cell in (BLACK_PAWN, BLACK_KING):
                    self.black_count += 1
    
    def check_game_over(self) -> Optional[str]:
        """Быстрая проверка окончания игры"""
        self.count_pieces()
        
        if self.white_count == 0:
            return "🏆 ЧЕРНЫЕ ПОБЕДИЛИ!"
        if self.black_count == 0:
            return "🏆 БЕЛЫЕ ПОБЕДИЛИ!"
        
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    if self.get_possible_moves(row, col):
                        return None
        
        winner = "⚫ ЧЕРНЫЕ" if self.current_player == "WHITE" else "⚪ БЕЛЫЕ"
        return f"🏆 {winner} ПОБЕДИЛИ!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Старт игры"""
    try:
        chat_id = update.effective_chat.id
        
        # Создаем новую игру
        game = CheckersGame()
        games[chat_id] = game
        
        text = f"🎮 НОВАЯ ИГРА\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
        
        message = await update.message.reply_text(
            text=text,
            reply_markup=create_board_markup(game)
        )
        
        game.message_id = message.message_id
        
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await update.message.reply_text("❌ Ошибка при запуске игры")

def create_board_markup(game: CheckersGame) -> InlineKeyboardMarkup:
    """Создание доски"""
    keyboard = []
    
    possible_moves = []
    if game.selected:
        from_row, from_col = game.selected
        possible_moves = game.get_possible_moves(from_row, from_col)
    
    moves_dict = {}
    for mr, mc, is_cap, _ in possible_moves:
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
        InlineKeyboardButton("🔄 Новая", callback_data="new")
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

async def click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кликов"""
    query = update.callback_query
    await query.answer()
    
    try:
        chat_id = update.effective_chat.id
        
        if chat_id not in games:
            await query.message.reply_text("❌ Игра не начата. Напишите /start")
            return
        
        game = games[chat_id]
        data = query.data
        
        if data == "draw":
            await query.message.reply_text("🤝 Игра окончена по соглашению")
            game.game_active = False
            return
        
        if data == "surrender":
            winner = "⚫ ЧЕРНЫЕ" if game.current_player == "WHITE" else "⚪ БЕЛЫЕ"
            await query.message.reply_text(f"🏳️ {winner} ПОБЕДИЛИ!")
            game.game_active = False
            return
        
        if data == "new":
            game._setup_board()
            text = f"🔄 НОВАЯ ИГРА\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
            await update_board(update, game, text)
            return
        
        if not game.game_active:
            await query.answer("Игра окончена, начните новую /start")
            return
        
        game_over = game.check_game_over()
        if game_over:
            await query.message.reply_text(f"🏁 {game_over}")
            game.game_active = False
            return
        
        row, col = map(int, data.split('_'))
        
        if (row + col) % 2 == 0:
            return
        
        cell = game.board[row][col]
        
        if game.selected is None:
            if game.current_player == "WHITE":
                if cell not in [WHITE_PAWN, WHITE_KING]:
                    if cell != EMPTY:
                        await query.answer("Сейчас ходят ⚪ БЕЛЫЕ!")
                    return
            else:
                if cell not in [BLACK_PAWN, BLACK_KING]:
                    if cell != EMPTY:
                        await query.answer("Сейчас ходят ⚫ ЧЕРНЫЕ!")
                    return
            
            must_capture = game.has_any_captures()
            if must_capture:
                forced_captures = game.get_forced_captures()
                if (row, col) not in forced_captures:
                    await query.answer("Сначала съешьте шашку противника!", show_alert=True)
                    return
            
            game.selected = (row, col)
            text = f"Выбрана шашка\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
            await update_board(update, game, text)
        
        else:
            from_row, from_col = game.selected
            from_cell = game.board[from_row][from_col]
            
            moves = game.get_possible_moves(from_row, from_col)
            
            selected_move = None
            for mr, mc, is_cap, enemy_pos in moves:
                if mr == row and mc == col:
                    selected_move = (mr, mc, is_cap, enemy_pos)
                    break
            
            if not selected_move:
                if (game.current_player == "WHITE" and cell in [WHITE_PAWN, WHITE_KING]) or \
                   (game.current_player == "BLACK" and cell in [BLACK_PAWN, BLACK_KING]):
                    
                    must_capture = game.has_any_captures()
                    if must_capture:
                        forced_captures = game.get_forced_captures()
                        if (row, col) not in forced_captures:
                            await query.answer("Сначала съешьте шашку противника!", show_alert=True)
                            return
                    
                    game.selected = (row, col)
                    await update_board(update, game, "Выбрана новая шашка")
                else:
                    await query.answer("❌ Неверный ход!", show_alert=True)
                return
            
            move_row, move_col, is_capture, enemy_pos = selected_move
            
            if not is_capture and game.has_any_captures():
                moves_for_this_piece = game.get_possible_moves(from_row, from_col)
                piece_has_captures = any(cap for _, _, cap, _ in moves_for_this_piece)
                
                if piece_has_captures:
                    await query.answer("Вы должны съесть шашку противника!", show_alert=True)
                    return
            
            game.board[move_row][move_col] = from_cell
            game.board[from_row][from_col] = EMPTY
            
            if is_capture and enemy_pos:
                enemy_row, enemy_col = enemy_pos
                game.board[enemy_row][enemy_col] = EMPTY
            
            game.check_promotion(move_row, move_col)
            game.count_pieces()
            
            if is_capture:
                moves_after = game.get_possible_moves(move_row, move_col)
                can_continue = any(cap for _, _, cap, _ in moves_after)
                
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
            
            game_over = game.check_game_over()
            if game_over:
                await query.message.reply_text(f"🏁 {game_over}")
                game.game_active = False
                return
            
            text = f"{msg}\nХод: {'⚪ БЕЛЫЕ' if game.current_player == 'WHITE' else '⚫ ЧЕРНЫЕ'}"
            await update_board(update, game, text)
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике: {e}")
        await query.answer("❌ Ошибка, попробуйте еще раз")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Правила игры"""
    rules_text = """🎮 РУССКИЕ ШАШКИ

Шашки: ⚪ ⚫ ⬜ ⬛

Как играть:
1. /start - начать игру
2. Выберите свою шашку
3. Ходите или бейте

‼️ Взятие обязательно!
🤝 Ничья 🏳️ Сдаться 🔄 Новая"""
    
    await update.message.reply_text(rules_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Справка"""
    await update.message.reply_text("""
🎮 КОМАНДЫ:
/start - начать игру
/rules - правила
/help - справка

Белые ходят первыми.""")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main() -> None:
    """Запуск бота для Scalingo"""
    # Проверка токена
    if not TOKEN or "AAHO2Eb6Lakd3gOsvQoS8PGLPTkVwbQHYMY" in TOKEN:
        logger.warning("Используется тестовый токен")
    
    print("=" * 40)
    print("🎮 БОТ ДЛЯ РУССКИХ ШАШЕК")
    print(f"Python: {os.environ.get('PYTHON_VERSION', '3.12')}")
    print(f"Токен: {'Установлен' if TOKEN else 'НЕ НАЙДЕН'}")
    print("=" * 40)
    
    # Простой запуск для Scalingo
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(click_handler))
    app.add_error_handler(error_handler)
    
    print("✅ Бот запущен!")
    print("👉 Отправьте /start в Telegram")
    print("=" * 40)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()