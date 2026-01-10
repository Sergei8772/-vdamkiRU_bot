import json
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

# Игровые константы
EMPTY = ' '
WHITE_PAWN = '⚪'
BLACK_PAWN = '⚫'
WHITE_KING = '⬜'
BLACK_KING = '⬛'

class CheckersGame:
    """Класс для игры в шашки с обязательным взятием"""
    
    def __init__(self):
        self.board = [[EMPTY] * 8 for _ in range(8)]
        self.selected: Optional[Tuple[int, int]] = None
        self.current_player = "WHITE"
        self.game_active = True
        self.white_count = 12
        self.black_count = 12
        self.move_history: List[Dict] = []
        self.must_capture = False  # Флаг обязательного взятия
        self.capture_chain = []    # Цепочка взятий для текущего хода
        
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
        self.move_history = []
        self.must_capture = False
        self.capture_chain = []
        
        # Расстановка шашек
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = BLACK_PAWN
        
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = WHITE_PAWN
    
    @staticmethod
    def from_json(board_state: str) -> 'CheckersGame':
        """Создать игру из JSON строки"""
        try:
            data = json.loads(board_state)
            game = CheckersGame()
            game.board = data['board']
            game.selected = tuple(data['selected']) if data['selected'] else None
            game.current_player = data['current_player']
            game.game_active = data['game_active']
            game.white_count = data['white_count']
            game.black_count = data['black_count']
            game.move_history = data.get('move_history', [])
            game.must_capture = data.get('must_capture', False)
            game.capture_chain = data.get('capture_chain', [])
            return game
        except Exception as e:
            logger.error(f"Error loading game from JSON: {e}")
            return CheckersGame()
    
    def to_json(self) -> str:
        """Сохранить игру в JSON строку"""
        data = {
            'board': self.board,
            'selected': list(self.selected) if self.selected else None,
            'current_player': self.current_player,
            'game_active': self.game_active,
            'white_count': self.white_count,
            'black_count': self.black_count,
            'move_history': self.move_history,
            'must_capture': self.must_capture,
            'capture_chain': self.capture_chain
        }
        return json.dumps(data, ensure_ascii=False)
    
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
        """Получение возможных ходов для шашки или дамки с учетом обязательных взятий"""
        piece = self.board[row][col]
        
        if piece == EMPTY:
            return []
        
        # Если есть обязательное взятие, возвращаем только взятия
        if self.must_capture and self.selected:
            # Продолжение взятия из выбранной шашки
            return self._get_captures(row, col, piece)
        elif self.has_any_captures():
            # Первое взятие - ищем все возможные взятия
            return self._get_captures(row, col, piece)
        else:
            # Нет обязательных взятий - обычные ходы
            return self._get_normal_moves(row, col, piece)
    
    def _get_normal_moves(self, row: int, col: int, piece: str) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]], List[Tuple[int, int]]]]:
        """Получение обычных ходов (без взятий)"""
        moves = []
        
        if piece in [WHITE_KING, BLACK_KING]:
            # Ходы для дамки
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                for step in range(1, 8):
                    new_row, new_col = row + dr * step, col + dc * step
                    if not (0 <= new_row < 8 and 0 <= new_col < 8):
                        break
                    
                    if self.board[new_row][new_col] == EMPTY:
                        moves.append((new_row, new_col, False, None, []))
                    else:
                        break
        else:
            # Ходы для простой шашки
            is_white = piece == WHITE_PAWN
            move_dirs = [(-1, -1), (-1, 1)] if is_white else [(1, -1), (1, 1)]
            
            for dr, dc in move_dirs:
                new_row, new_col = row + dr, col + dc
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    if self.board[new_row][new_col] == EMPTY:
                        moves.append((new_row, new_col, False, None, []))
        
        return moves
    
    def _get_captures(self, row: int, col: int, piece: str) -> List[Tuple[int, int, bool, Optional[Tuple[int, int]], List[Tuple[int, int]]]]:
        """Получение всех возможных взятий для шашки"""
        moves = []
        
        def find_captures(r: int, c: int, captured: List[Tuple[int, int]], max_depth: int = 20):
            """Рекурсивный поиск взятий с ограничением глубины"""
            if len(captured) >= max_depth:
                return
            
            is_white = piece in [WHITE_PAWN, WHITE_KING]
            enemy_pieces = [BLACK_PAWN, BLACK_KING] if is_white else [WHITE_PAWN, WHITE_KING]
            is_king = piece in [WHITE_KING, BLACK_KING]
            
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            
            for dr, dc in directions:
                # Для дамки ищем врага на линии
                if is_king:
                    for step in range(1, 8):
                        check_row, check_col = r + dr * step, c + dc * step
                        if not (0 <= check_row < 8 and 0 <= check_col < 8):
                            break
                        
                        cell = self.board[check_row][check_col]
                        
                        # Нашли врага
                        if cell in enemy_pieces and (check_row, check_col) not in captured:
                            # Ищем пустую клетку за врагом
                            for step2 in range(step + 1, 8):
                                land_row, land_col = r + dr * step2, c + dc * step2
                                if not (0 <= land_row < 8 and 0 <= land_col < 8):
                                    break
                                
                                if self.board[land_row][land_col] == EMPTY:
                                    new_captured = captured + [(check_row, check_col)]
                                    # Проверяем, что такой ход еще не добавлен
                                    if not any(mr == land_row and mc == land_col for mr, mc, _, _, _ in moves):
                                        moves.append((land_row, land_col, True, (check_row, check_col), new_captured))
                                    # Рекурсивно ищем дальше
                                    find_captures(land_row, land_col, new_captured, max_depth)
                                else:
                                    break
                            break  # Прерываем поиск по этой линии после найденного врага
                        elif cell != EMPTY:
                            break  # Прерываем если нашли свою шашку
                
                else:
                    # Для простой шашки
                    # Проверяем соседнюю клетку
                    check_row, check_col = r + dr, c + dc
                    if 0 <= check_row < 8 and 0 <= check_col < 8:
                        if self.board[check_row][check_col] in enemy_pieces and (check_row, check_col) not in captured:
                            # Проверяем клетку за врагом
                            land_row, land_col = r + dr * 2, c + dc * 2
                            if 0 <= land_row < 8 and 0 <= land_col < 8:
                                if self.board[land_row][land_col] == EMPTY:
                                    new_captured = captured + [(check_row, check_col)]
                                    # Проверяем, что такой ход еще не добавлен
                                    if not any(mr == land_row and mc == land_col for mr, mc, _, _, _ in moves):
                                        moves.append((land_row, land_col, True, (check_row, check_col), new_captured))
                                    # Рекурсивно ищем дальше
                                    find_captures(land_row, land_col, new_captured, max_depth)
        
        find_captures(row, col, self.capture_chain)
        return moves
    
    def has_any_captures(self) -> bool:
        """Проверка обязательных взятий для текущего игрока"""
        current_pieces = [WHITE_PAWN, WHITE_KING] if self.current_player == "WHITE" else [BLACK_PAWN, BLACK_KING]
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    captures = self._get_captures(row, col, self.board[row][col])
                    if captures:
                        return True
        return False
    
    def get_forced_captures(self) -> List[Tuple[int, int]]:
        """Получение шашек с обязательными взятиями"""
        forced = []
        current_pieces = [WHITE_PAWN, WHITE_KING] if self.current_player == "WHITE" else [BLACK_PAWN, BLACK_KING]
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    captures = self._get_captures(row, col, self.board[row][col])
                    if captures:
                        forced.append((row, col))
        
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
            return "⚫ ЧЕРНЫЕ ПОБЕДИЛИ!"
        if self.black_count == 0:
            return "⚪ БЕЛЫЕ ПОБЕДИЛИ!"
        
        # Проверяем, есть ли у текущего игрока возможные ходы
        current_pieces = (WHITE_PAWN, WHITE_KING) if self.current_player == "WHITE" else (BLACK_PAWN, BLACK_KING)
        
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and self.board[row][col] in current_pieces:
                    moves = self.get_possible_moves(row, col)
                    if moves:
                        return None
        
        winner = "⚫ ЧЕРНЫЕ" if self.current_player == "WHITE" else "⚪ БЕЛЫЕ"
        return f"🏆 {winner} ПОБЕДИЛИ!"
    
    def make_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> Tuple[bool, str]:
        """Сделать ход с поддержкой цепочек взятий"""
        if self.board[from_row][from_col] == EMPTY:
            return False, "❌ На этой клетке нет шашки!"
        
        piece = self.board[from_row][from_col]
        current_pieces = ['⚪', '⬜'] if self.current_player == "WHITE" else ['⚫', '⬛']
        if piece not in current_pieces:
            return False, "❌ Это не ваша шашка!"
        
        # Получаем все возможные ходы
        possible_moves = self.get_possible_moves(from_row, from_col)
        
        # Ищем выбранный ход
        selected_move = None
        for move in possible_moves:
            move_row, move_col, is_capture, enemy_pos, captured_list = move
            if move_row == to_row and move_col == to_col:
                selected_move = move
                break
        
        if not selected_move:
            return False, "❌ Неверный ход!"
        
        move_row, move_col, is_capture, enemy_pos, captured_list = selected_move
        
        # Сохраняем ход
        move_record = {
            'from': (from_row, from_col),
            'to': (move_row, move_col),
            'piece': piece,
            'capture': is_capture,
            'captured': captured_list,
            'player': self.current_player
        }
        self.move_history.append(move_record)
        
        # Перемещаем шашку
        self.board[move_row][move_col] = piece
        self.board[from_row][from_col] = EMPTY
        
        # Удаляем съеденные шашки
        if is_capture:
            for cap_row, cap_col in captured_list:
                self.board[cap_row][cap_col] = EMPTY
            
            # Добавляем к цепочке взятий
            self.capture_chain.extend(captured_list)
        
        # Проверяем превращение
        promoted = self.check_promotion(move_row, move_col)
        
        # Важно: обновляем piece после превращения
        if promoted:
            piece = self.board[move_row][move_col]
        
        # Проверяем, можно ли продолжить взятие
        if is_capture:
            # Ищем дальнейшие взятия
            further_captures = self._get_captures(move_row, move_col, piece)
            
            if further_captures:
                # Можно продолжать взятие
                self.must_capture = True
                self.selected = (move_row, move_col)
                self.count_pieces()
                
                message = "✅ Съедено! Бейте дальше!"
                if promoted:
                    message += " Шашка превратилась в дамку!"
                return True, message
        
        # Ход завершен
        self.selected = None
        self.must_capture = False
        self.capture_chain = []
        self.current_player = "BLACK" if self.current_player == "WHITE" else "WHITE"
        
        self.count_pieces()
        
        message = "✅ Ход сделан!"
        if promoted:
            message += " Шашка превратилась в дамку!"
        if is_capture:
            message = f"✅ Съедено {len(captured_list)} шашек!"
        
        return True, message