import random
import math
from typing import List, Tuple, Optional, Dict, Any
from game_logic import CheckersGame


class CheckersAI:
    """Искусственный интеллект для игры в шашки"""

    def __init__(self, color: str = "BLACK"):
        self.color = color
        self.opponent_color = "WHITE" if color == "BLACK" else "BLACK"

    def get_best_move(self, game: CheckersGame) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Получить лучший ход для текущей позиции"""
        try:
            all_moves = self.get_all_possible_moves(game)
            
            if not all_moves:
                return None

            # Если есть обязательные взятия
            if game.has_any_captures():
                # Собираем все взятия
                capture_moves = []
                for move in all_moves:
                    (fr, fc), (tr, tc) = move
                    moves_list = game.get_possible_moves(fr, fc)
                    for mr, mc, is_cap, _, _ in moves_list:
                        if mr == tr and mc == tc and is_cap:
                            capture_moves.append(move)
                            break
                
                if capture_moves:
                    # Выбираем взятие с максимальным количеством съеденных шашек
                    best_capture = None
                    max_captured = -1
                    
                    for move in capture_moves:
                        (fr, fc), (tr, tc) = move
                        moves_list = game.get_possible_moves(fr, fc)
                        for mr, mc, is_cap, _, captured_list in moves_list:
                            if mr == tr and mc == tc and is_cap:
                                captured_count = len(captured_list)
                                if captured_count > max_captured:
                                    max_captured = captured_count
                                    best_capture = move
                                elif captured_count == max_captured:
                                    # При равном количестве берем случайный
                                    if random.random() > 0.5:
                                        best_capture = move
                                break
                    
                    if best_capture:
                        return best_capture
                    else:
                        # Если что-то пошло не так, берем первый ход взятия
                        return capture_moves[0] if capture_moves else None
            
            # Для обычных ходов используем упрощенную эвристику
            return self._get_simple_move(game, all_moves)
            
        except Exception as e:
            print(f"AI error: {e}")
            # Возвращаем случайный ход в случае ошибки
            return self._get_random_move(game)

    def get_all_possible_moves(self, game: CheckersGame) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Получить все возможные ходы для текущего игрока"""
        moves = []

        current_pieces = ('⚪', '⬜') if game.current_player == "WHITE" else ('⚫', '⬛')

        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    if game.board[row][col] in current_pieces:
                        piece_moves = game.get_possible_moves(row, col)
                        for mr, mc, _, _, _ in piece_moves:
                            moves.append(((row, col), (mr, mc)))

        return moves

    def _get_simple_move(self, game: CheckersGame, all_moves: List) -> Optional[Tuple]:
        """Упрощенный алгоритм выбора хода"""
        if not all_moves:
            return None

        # Собираем простую статистику по ходам
        moves_with_scores = []
        
        for move in all_moves:
            (fr, fc), (tr, tc) = move
            score = 0
            
            # Получаем информацию о ходе
            piece = game.board[fr][fc]
            is_king = piece in ['⬜', '⬛']
            
            # 1. Предпочтение ходам вперед
            if self.color == "BLACK":  # Черные ходят вниз
                if tr > fr:  # Движение вниз
                    score += 2 if not is_king else 0
                elif is_king and tr < fr:  # Дамка может ходить назад
                    score += 1
                if tr == 7 and not is_king:  # Превращение в дамку
                    score += 10
            else:  # Белые ходят вверх
                if tr < fr:  # Движение вверх
                    score += 2 if not is_king else 0
                elif is_king and tr > fr:  # Дамка может ходить назад
                    score += 1
                if tr == 0 and not is_king:  # Превращение в дамку
                    score += 10
            
            # 2. Предпочтение ходам в центр (защита)
            center_distance = abs(tr - 3.5) + abs(tc - 3.5)
            if is_king:
                score -= center_distance * 0.2
            else:
                score -= center_distance * 0.3
            
            # 3. Предпочтение защищенным позициям (боковые колонки)
            if tc == 0 or tc == 7:
                score += 1
            
            # 4. Небольшая случайность для разнообразия
            score += random.uniform(0, 0.5)
            
            moves_with_scores.append((score, move))
        
        # Выбираем ход с максимальным скором
        moves_with_scores.sort(reverse=True, key=lambda x: x[0])
        return moves_with_scores[0][1]

    def _get_random_move(self, game: CheckersGame) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Получить случайный ход (fallback)"""
        all_moves = self.get_all_possible_moves(game)
        if not all_moves:
            return None
        return random.choice(all_moves)


class BotPlayer:
    """Класс для управления игрой против бота"""

    def __init__(self):
        self.ai = None
        self.game = None
        self.player_color = "WHITE"
        self.bot_color = "BLACK"

    def setup_game(self) -> CheckersGame:
        """Настроить новую игру"""
        self.game = CheckersGame()
        self.ai = CheckersAI(color=self.bot_color)
        return self.game

    def make_bot_move(self) -> Tuple[bool, str]:
        """Бот делает ход"""
        if not self.game or self.game.current_player != self.bot_color:
            return False, "Сейчас не ход бота"

        try:
            best_move = self.ai.get_best_move(self.game)

            if not best_move:
                return False, "У бота нет возможных ходов"

            (fr, fc), (tr, tc) = best_move
            success, message = self.game.make_move(fr, fc, tr, tc)

            return success, message
        except Exception as e:
            print(f"Bot error: {e}")
            # В случае ошибки пытаемся сделать случайный ход
            all_moves = self.ai.get_all_possible_moves(self.game)
            if all_moves:
                random_move = random.choice(all_moves)
                (fr, fc), (tr, tc) = random_move
                success, message = self.game.make_move(fr, fc, tr, tc)
                return success, f"✅ Случайный ход: {message}"
            return False, "❌ Ошибка бота"

    def make_player_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> Tuple[bool, str]:
        """Игрок делает ход"""
        if not self.game or self.game.current_player != self.player_color:
            return False, "Сейчас не ваш ход"

        success, message = self.game.make_move(from_row, from_col, to_row, to_col)
        return success, message

    def check_game_over(self) -> Optional[str]:
        """Проверить окончание игры"""
        if self.game:
            return self.game.check_game_over()
        return None