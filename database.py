import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Инициализация базы данных"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                games_lost INTEGER DEFAULT 0,
                games_draw INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица активных игр
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_games (
                game_id TEXT PRIMARY KEY,
                chat_id INTEGER,
                player1_id INTEGER,
                player2_id INTEGER,
                player1_name TEXT,
                player2_name TEXT,
                player1_color TEXT DEFAULT 'WHITE',
                player2_color TEXT DEFAULT 'BLACK',
                current_player_id INTEGER,
                board_state TEXT,
                selected_cell TEXT,
                last_move_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                game_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE', -- ACTIVE, WAITING, FINISHED
                move_count INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица завершенных игр
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS finished_games (
                game_id TEXT PRIMARY KEY,
                chat_id INTEGER,
                player1_id INTEGER,
                player2_id INTEGER,
                winner_id INTEGER,
                result TEXT, -- WIN, LOSS, DRAW, SURRENDER, TIMEOUT
                moves_history TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                game_duration INTEGER,
                white_count INTEGER,
                black_count INTEGER
            )
        ''')
        
        # Таблица приглашений (упрощенная версия)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                invitation_id TEXT PRIMARY KEY,
                chat_id INTEGER,
                from_user_id INTEGER,
                from_user_name TEXT,
                to_user_id INTEGER,
                to_user_name TEXT,
                status TEXT DEFAULT 'PENDING', -- PENDING, ACCEPTED, DECLINED, EXPIRED
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        return sqlite3.connect(self.db_path)
    
    # === Методы для пользователей ===
    
    def get_or_create_user(self, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Получить или создать пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Пытаемся получить пользователя
        cursor.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        user = cursor.fetchone()
        
        if user:
            # Обновляем активность существующего пользователя
            cursor.execute(
                'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?',
                (user_id,)
            )
            # Получаем обновленные данные
            cursor.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            )
            user = cursor.fetchone()
            columns = [description[0] for description in cursor.description]
            user_dict = dict(zip(columns, user))
        else:
            # Создаем нового пользователя
            cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            
            # Получаем созданного пользователя
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            columns = [description[0] for description in cursor.description]
            user_dict = dict(zip(columns, user))
        
        conn.commit()
        conn.close()
        
        return user_dict
    
    def update_user_stats(self, user_id: int, result: str) -> None:
        """Обновить статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if result == 'WIN':
            cursor.execute(
                'UPDATE users SET games_played = games_played + 1, games_won = games_won + 1, rating = rating + 10 WHERE user_id = ?',
                (user_id,)
            )
        elif result == 'LOSS':
            cursor.execute(
                'UPDATE users SET games_played = games_played + 1, games_lost = games_lost + 1, rating = rating - 5 WHERE user_id = ?',
                (user_id,)
            )
        elif result == 'DRAW':
            cursor.execute(
                'UPDATE users SET games_played = games_played + 1, games_draw = games_draw + 1, rating = rating + 2 WHERE user_id = ?',
                (user_id,)
            )
        
        conn.commit()
        conn.close()
    
    # === Методы для игр ===
    
    def create_game(self, game_id: str, chat_id: int, player1_id: int, player2_id: int,
                   player1_name: str, player2_name: str, board_state: str) -> bool:
        """Создать новую игру"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO active_games 
                (game_id, chat_id, player1_id, player2_id, player1_name, player2_name,
                 current_player_id, board_state, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            ''', (game_id, chat_id, player1_id, player2_id, player1_name, player2_name,
                  player1_id, board_state))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating game: {e}")
            return False
    
    def get_active_game(self, chat_id: int, game_id: str = None) -> Optional[Dict[str, Any]]:
        """Получить активную игру в чате"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if game_id:
            cursor.execute(
                'SELECT * FROM active_games WHERE chat_id = ? AND game_id = ? AND status = "ACTIVE"',
                (chat_id, game_id)
            )
        else:
            cursor.execute(
                'SELECT * FROM active_games WHERE chat_id = ? AND status = "ACTIVE"',
                (chat_id,)
            )
        
        game = cursor.fetchone()
        
        if game:
            columns = [description[0] for description in cursor.description]
            game_dict = dict(zip(columns, game))
        else:
            game_dict = None
        
        conn.close()
        return game_dict
    
    def update_game_state(self, game_id: str, board_state: str, current_player_id: int,
                         selected_cell: str = None) -> None:
        """Обновить состояние игры"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if selected_cell:
            cursor.execute('''
                UPDATE active_games 
                SET board_state = ?, current_player_id = ?, selected_cell = ?,
                    move_count = move_count + 1, last_move_time = CURRENT_TIMESTAMP
                WHERE game_id = ?
            ''', (board_state, current_player_id, selected_cell, game_id))
        else:
            cursor.execute('''
                UPDATE active_games 
                SET board_state = ?, current_player_id = ?,
                    move_count = move_count + 1, last_move_time = CURRENT_TIMESTAMP
                WHERE game_id = ?
            ''', (board_state, current_player_id, game_id))
        
        conn.commit()
        conn.close()
    
    def finish_game(self, game_id: str, winner_id: int = None, result: str = "DRAW",
                   moves_history: str = "", white_count: int = 0, black_count: int = 0) -> None:
        """Завершить игру"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем данные об игре
        cursor.execute(
            'SELECT * FROM active_games WHERE game_id = ?',
            (game_id,)
        )
        game = cursor.fetchone()
        
        if not game:
            conn.close()
            return
        
        columns = [description[0] for description in cursor.description]
        game_dict = dict(zip(columns, game))
        
        # Рассчитываем длительность игры
        cursor.execute(
            'SELECT julianday(CURRENT_TIMESTAMP) - julianday(game_start_time) FROM active_games WHERE game_id = ?',
            (game_id,)
        )
        duration_result = cursor.fetchone()
        if duration_result and duration_result[0]:
            duration = duration_result[0] * 24 * 3600  # в секундах
        else:
            duration = 0
        
        # Переносим в таблицу завершенных игр
        cursor.execute('''
            INSERT INTO finished_games 
            (game_id, chat_id, player1_id, player2_id, winner_id, result,
             moves_history, start_time, game_duration, white_count, black_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (game_id, game_dict['chat_id'], game_dict['player1_id'], 
              game_dict['player2_id'], winner_id, result, moves_history,
              game_dict['game_start_time'], int(duration), white_count, black_count))
        
        # Удаляем из активных игр
        cursor.execute('DELETE FROM active_games WHERE game_id = ?', (game_id,))
        
        # Обновляем статистику игроков
        if winner_id:
            loser_id = game_dict['player2_id'] if winner_id == game_dict['player1_id'] else game_dict['player1_id']
            self.update_user_stats(winner_id, 'WIN')
            self.update_user_stats(loser_id, 'LOSS')
        else:
            self.update_user_stats(game_dict['player1_id'], 'DRAW')
            self.update_user_stats(game_dict['player2_id'], 'DRAW')
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            columns = [description[0] for description in cursor.description]
            user_dict = dict(zip(columns, user))
            
            # Рассчитываем проценты
            total = user_dict['games_played']
            if total > 0:
                user_dict['win_rate'] = (user_dict['games_won'] / total) * 100
                user_dict['loss_rate'] = (user_dict['games_lost'] / total) * 100
                user_dict['draw_rate'] = (user_dict['games_draw'] / total) * 100
            else:
                user_dict['win_rate'] = user_dict['loss_rate'] = user_dict['draw_rate'] = 0
            
            return user_dict
        
        # Возвращаем дефолтные значения для нового пользователя
        return {
            'user_id': user_id,
            'games_played': 0,
            'games_won': 0,
            'games_lost': 0,
            'games_draw': 0,
            'rating': 1000,
            'win_rate': 0,
            'loss_rate': 0,
            'draw_rate': 0
        }
    
    def get_chat_games_count(self, chat_id: int) -> int:
        """Получить количество активных игр в чате"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT COUNT(*) FROM active_games WHERE chat_id = ? AND status = "ACTIVE"',
            (chat_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def get_active_games_in_chat(self, chat_id: int) -> List[Dict[str, Any]]:
        """Получить все активные игры в чате"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM active_games WHERE chat_id = ? AND status = "ACTIVE"',
            (chat_id,)
        )
        
        games = cursor.fetchall()
        result = []
        
        if games:
            columns = [description[0] for description in cursor.description]
            for game in games:
                game_dict = dict(zip(columns, game))
                result.append(game_dict)
        
        conn.close()
        return result