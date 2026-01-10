import random
import math
from typing import List, Tuple, Optional, Dict, Any
from game_logic import CheckersGame


class CheckersAI:
    """Оптимизированный искусственный интеллект для игры в шашки"""
    
    def __init__(self, color: str = "BLACK"):
        self.color = color
        self.opponent_color = "WHITE" if color == "BLACK" else "BLACK"
        
        # Кэш для быстрого поиска ходов
        self._move_cache = {}
        self._evaluation_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _get_board_key(self, game: CheckersGame) -> str:
        """Генерировать ключ для кэша на основе состояния доски"""
        board_key = []
        for row in game.board:
            for cell in row:
                board_key.append(cell)
        return ''.join(board_key) + game.current_player + str(game.must_capture)
    
    def get_best_move(self, game: CheckersGame) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Получить лучший ход для текущей позиции"""
        board_key = self._get_board_key(game)
        
        # Проверяем кэш
        if board_key in self._move_cache:
            self._cache_hits += 1
            return self._move_cache[board_key]
        
        self._cache_misses += 1
        
        try:
            all_moves = self.get_all_possible_moves(game)
            
            if not all_moves:
                self._move_cache[board_key] = None
                return None
            
            # Особый случай: продолжение цепочки взятий
            if game.must_capture and game.selected:
                # Берем только продолжения взятия из выбранной шашки
                capture_moves = []
                row, col = game.selected
                piece = game.board[row][col]
                possible_moves = game.get_possible_moves(row, col)
                
                for mr, mc, is_cap, _, captured_list in possible_moves:
                    if is_cap:
                        capture_moves.append(((row, col), (mr, mc)))
                
                if capture_moves:
                    # Выбираем самое длинное взятие
                    return self._select_best_capture_continuation(game, capture_moves)
            
            # Если есть обязательные взятия (начало цепочки)
            if game.has_any_captures():
                # Получаем все взятия
                capture_moves = self._get_all_capture_moves(game, all_moves)
                
                if capture_moves:
                    # Выбираем взятие с максимальным количеством съеденных шашек
                    best_capture = self._select_best_capture(game, capture_moves)
                    
                    if best_capture:
                        self._move_cache[board_key] = best_capture
                        return best_capture
                    else:
                        # Если что-то пошло не так, берем первое взятие
                        if capture_moves:
                            self._move_cache[board_key] = capture_moves[0]
                            return capture_moves[0]
            
            # Для обычных ходов используем оптимизированную эвристику
            best_move = self._get_optimized_move(game, all_moves)
            self._move_cache[board_key] = best_move
            
            return best_move
            
        except Exception as e:
            print(f"AI error: {e}")
            # Возвращаем случайный ход в случае ошибки
            all_moves = self.get_all_possible_moves(game)
            if all_moves:
                move = random.choice(all_moves)
                self._move_cache[board_key] = move
                return move
            return None
    
    def _select_best_capture_continuation(self, game: CheckersGame, capture_moves: List) -> Optional[Tuple]:
        """Выбрать лучшее продолжение взятия"""
        if not capture_moves:
            return None
        
        best_move = None
        max_captured = -1
        
        for move in capture_moves:
            (fr, fc), (tr, tc) = move
            moves_list = game.get_possible_moves(fr, fc)
            
            # Ищем информацию о взятии
            capture_info = None
            for mr, mc, is_cap, _, captured_list in moves_list:
                if mr == tr and mc == tc and is_cap:
                    capture_info = (is_cap, captured_list)
                    break
            
            if capture_info:
                _, captured_list = capture_info
                captured_count = len(captured_list)
                
                # Учитываем превращение в дамку
                piece = game.board[fr][fc]
                if piece in ['⚪', '⚫']:
                    if (game.current_player == "WHITE" and tr == 0) or \
                       (game.current_player == "BLACK" and tr == 7):
                        captured_count += 3  # Бонус за превращение
                
                if captured_count > max_captured:
                    max_captured = captured_count
                    best_move = move
                elif captured_count == max_captured:
                    # При равном количестве предпочитаем ходы с превращением
                    piece = game.board[fr][fc]
                    if piece in ['⚪', '⚫']:
                        if (game.current_player == "WHITE" and tr == 0) or \
                           (game.current_player == "BLACK" and tr == 7):
                            best_move = move
        
        return best_move if best_move else capture_moves[0]
    
    def get_all_possible_moves(self, game: CheckersGame) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Получить все возможные ходы для текущего игрока"""
        # Используем оптимизированный метод из game_logic
        return game.get_all_possible_moves_for_current_player()
    
    def _get_all_capture_moves(self, game: CheckersGame, all_moves: List) -> List:
        """Получить только ходы со взятием"""
        capture_moves = []
        
        for move in all_moves:
            (fr, fc), (tr, tc) = move
            moves_list = game.get_possible_moves(fr, fc)
            for mr, mc, is_cap, _, _ in moves_list:
                if mr == tr and mc == tc and is_cap:
                    capture_moves.append(move)
                    break
        
        return capture_moves
    
    def _select_best_capture(self, game: CheckersGame, capture_moves: List) -> Optional[Tuple]:
        """Выбрать лучшее взятие"""
        if not capture_moves:
            return None
        
        best_move = None
        max_score = -float('inf')
        
        for move in capture_moves:
            (fr, fc), (tr, tc) = move
            moves_list = game.get_possible_moves(fr, fc)
            
            # Ищем информацию о взятии
            capture_info = None
            for mr, mc, is_cap, _, captured_list in moves_list:
                if mr == tr and mc == tc and is_cap:
                    capture_info = (is_cap, captured_list)
                    break
            
            if capture_info:
                _, captured_list = capture_info
                score = len(captured_list) * 10  # Базовый счет за количество съеденных
                
                # Бонус за превращение в дамку
                piece = game.board[fr][fc]
                if piece in ['⚪', '⚫']:
                    if (game.current_player == "WHITE" and tr == 0) or \
                       (game.current_player == "BLACK" and tr == 7):
                        score += 15
                
                # Бонус за съедание дамки
                for cr, cc in captured_list:
                    if game.board[cr][cc] in ['⬜', '⬛']:
                        score += 20
                
                # Штраф за опасную позицию после взятия
                if self._is_dangerous_position(game, tr, tc, piece):
                    score -= 5
                
                if score > max_score:
                    max_score = score
                    best_move = move
                elif score == max_score and random.random() > 0.5:
                    best_move = move
        
        return best_move
    
    def _is_dangerous_position(self, game: CheckersGame, row: int, col: int, piece: str) -> bool:
        """Проверить, находится ли шашка в опасной позиции"""
        is_white = piece in ['⚪', '⬜']
        enemy_color = "BLACK" if is_white else "WHITE"
        
        # Проверяем соседние клетки на наличие вражеских шашек
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            check_row, check_col = row + dr, col + dc
            if 0 <= check_row < 8 and 0 <= check_col < 8:
                enemy_piece = game.board[check_row][check_col]
                if is_white and enemy_piece in ['⚫', '⬛']:
                    # Проверяем, может ли враг съесть
                    land_row, land_col = row - dr, col - dc
                    if 0 <= land_row < 8 and 0 <= land_col < 8:
                        if game.board[land_row][land_col] == ' ':
                            return True
                elif not is_white and enemy_piece in ['⚪', '⬜']:
                    # Проверяем, может ли враг съесть
                    land_row, land_col = row - dr, col - dc
                    if 0 <= land_row < 8 and 0 <= land_col < 8:
                        if game.board[land_row][land_col] == ' ':
                            return True
        
        return False
    
    def _get_optimized_move(self, game: CheckersGame, all_moves: List) -> Optional[Tuple]:
        """Оптимизированный алгоритм выбора хода"""
        if not all_moves:
            return None
        
        moves_with_scores = []
        
        for move in all_moves:
            (fr, fc), (tr, tc) = move
            score = 0
            
            # Получаем информацию о шашке
            piece = game.board[fr][fc]
            is_king = piece in ['⬜', '⬛']
            is_white = piece in ['⚪', '⬜']
            
            # 1. Предпочтение ходам вперед для простых шашек
            if not is_king:
                if is_white and tr < fr:  # Белые идут вверх
                    score += 3
                elif not is_white and tr > fr:  # Черные идут вниз
                    score += 3
            
            # 2. Бонус за превращение в дамку
            if not is_king:
                if is_white and tr == 0:
                    score += 20
                elif not is_white and tr == 7:
                    score += 20
            
            # 3. Предпочтение защищенным позициям (боковые колонки)
            if tc == 0 or tc == 7:
                score += 2
            
            # 4. Предпочтение центру (для дамок и защиты)
            if 2 <= tr <= 5 and 2 <= tc <= 5:
                score += 1
            
            # 5. Штраф за опасные позиции
            if self._is_dangerous_position(game, tr, tc, piece):
                score -= 4
            
            # 6. Бонус за движение к центру (для защиты)
            center_distance = abs(tr - 3.5) + abs(tc - 3.5)
            if is_king:
                score -= center_distance * 0.1
            else:
                score -= center_distance * 0.2
            
            # 7. Предпочтение не оставлять шашку под боем
            if not self._is_under_attack(game, fr, fc, piece) and self._is_under_attack(game, tr, tc, piece):
                score -= 3
            
            # 8. Небольшая случайность для разнообразия
            score += random.uniform(0, 1.0)
            
            moves_with_scores.append((score, move))
        
        # Сортируем по убыванию счета
        moves_with_scores.sort(reverse=True, key=lambda x: x[0])
        
        # Берем лучший ход
        return moves_with_scores[0][1]
    
    def _is_under_attack(self, game: CheckersGame, row: int, col: int, piece: str) -> bool:
        """Проверить, находится ли шашка под атакой"""
        is_white = piece in ['⚪', '⬜']
        enemy_pieces = ['⚫', '⬛'] if is_white else ['⚪', '⬜']
        
        # Проверяем все направления
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            # Для простых шашек враг должен быть на соседней клетке
            check_row, check_col = row + dr, col + dc
            if 0 <= check_row < 8 and 0 <= check_col < 8:
                if game.board[check_row][check_col] in enemy_pieces:
                    # Проверяем, есть ли пустая клетка за нашей шашкой
                    land_row, land_col = row - dr, col - dc
                    if 0 <= land_row < 8 and 0 <= land_col < 8:
                        if game.board[land_row][land_col] == ' ':
                            return True
            
            # Для дамок проверяем всю линию
            if piece in ['⬜', '⬛']:
                for step in range(1, 8):
                    check_row, check_col = row + dr * step, col + dc * step
                    if not (0 <= check_row < 8 and 0 <= check_col < 8):
                        break
                    
                    cell = game.board[check_row][check_col]
                    if cell in enemy_pieces:
                        # Проверяем, есть ли пустая клетка за нами
                        for step2 in range(step + 1, 8):
                            land_row, land_col = row + dr * step2, col + dc * step2
                            if not (0 <= land_row < 8 and 0 <= land_col < 8):
                                break
                            if game.board[land_row][land_col] == ' ':
                                return True
                        break
                    elif cell != ' ':
                        break
        
        return False
    
    def clear_cache(self):
        """Очистить кэш ИИ"""
        self._move_cache.clear()
        self._evaluation_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Получить статистику кэша"""
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        }


class BotPlayer:
    """Оптимизированный класс для управления игрой против бота"""
    
    def __init__(self):
        self.ai = None
        self.game = None
        self.player_color = "WHITE"
        self.bot_color = "BLACK"
        self.move_count = 0
    
    def setup_game(self) -> CheckersGame:
        """Настроить новую игру"""
        self.game = CheckersGame()
        self.ai = CheckersAI(color=self.bot_color)
        self.move_count = 0
        return self.game
    
    def make_bot_move(self) -> Tuple[bool, str]:
        """Бот делает ход"""
        if not self.game or self.game.current_player != self.bot_color:
            return False, "Сейчас не ход бота"
        
        try:
            # Очищаем кэш каждые 10 ходов
            if self.move_count > 0 and self.move_count % 10 == 0:
                self.ai.clear_cache()
            
            # Особый случай: если бот должен продолжить взятие
            if self.game.must_capture and self.game.selected:
                row, col = self.game.selected
                piece = self.game.board[row][col]
                print(f"🤖 Бот продолжает взятие с ({row}, {col}), фигура: {piece}")
            
            best_move = self.ai.get_best_move(self.game)
            
            if not best_move:
                return False, "У бота нет возможных ходов"
            
            (fr, fc), (tr, tc) = best_move
            success, message = self.game.make_move(fr, fc, tr, tc)
            
            if success:
                self.move_count += 1
                # Проверяем, не превратилась ли шашка в дамку
                if self.game.board[tr][tc] in ['⬜', '⬛'] and piece in ['⚪', '⚫']:
                    print(f"🤖 Бот превратил шашку в дамку на ({tr}, {tc})!")
            
            return success, message
        except Exception as e:
            print(f"Bot error: {e}")
            # В случае ошибки пытаемся сделать случайный ход
            all_moves = self.ai.get_all_possible_moves(self.game)
            if all_moves:
                random_move = random.choice(all_moves)
                (fr, fc), (tr, tc) = random_move
                success, message = self.game.make_move(fr, fc, tr, tc)
                if success:
                    self.move_count += 1
                return success, f"✅ Случайный ход: {message}"
            return False, "❌ Ошибка бота"
    
    def make_player_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> Tuple[bool, str]:
        """Игрок делает ход"""
        if not self.game or self.game.current_player != self.player_color:
            return False, "Сейчас не ваш ход"
        
        success, message = self.game.make_move(from_row, from_col, to_row, to_col)
        
        if success and self.game.current_player == self.bot_color:
            self.move_count += 1
        
        return success, message
    
    def check_game_over(self) -> Optional[str]:
        """Проверка окончания игры"""
        if self.game:
            return self.game.check_game_over()
        return None