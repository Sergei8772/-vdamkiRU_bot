import random
import string
from typing import Optional, Tuple
from datetime import datetime, timedelta

def generate_game_id(length: int = 8) -> str:
    """Сгенерировать уникальный ID игры"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_player_color_symbol(player_color: str, is_king: bool = False) -> str:
    """Получить символ шашки по цвету"""
    if player_color == "WHITE":
        return "⬜" if is_king else "⚪"
    else:
        return "⬛" if is_king else "⚫"

def format_game_status(game_status: dict) -> str:
    """Отформатировать статус игры в читаемый текст"""
    player1 = game_status.get('player1_name', 'Игрок 1')
    player2 = game_status.get('player2_name', 'Игрок 2')
    current_player = game_status.get('current_player_id')
    
    if current_player == game_status.get('player1_id'):
        current_turn = f"{player1} (⚪ Белые)"
    else:
        current_turn = f"{player2} (⚫ Черные)"
    
    return f"""🎮 Активная игра

⚪ Белые: {player1}
⚫ Черные: {player2}

Ход: {current_turn}
Ходов сделано: {game_status.get('move_count', 0)}
"""

def format_user_stats(stats: dict) -> str:
    """Отформатировать статистику пользователя"""
    total = stats.get('games_played', 0)
    
    if total == 0:
        return "📊 У вас еще нет сыгранных игр.\nНачните первую игру!"
    
    win_rate = stats.get('win_rate', 0)
    loss_rate = stats.get('loss_rate', 0)
    draw_rate = stats.get('draw_rate', 0)
    
    return f"""📊 Ваша статистика:

🎮 Всего игр: {total}
🏆 Побед: {stats.get('games_won', 0)} ({win_rate:.1f}%)
💔 Поражений: {stats.get('games_lost', 0)} ({loss_rate:.1f}%)
🤝 Ничьих: {stats.get('games_draw', 0)} ({draw_rate:.1f}%)

⭐ Рейтинг: {stats.get('rating', 1000)}
"""

def parse_callback_data(data: str) -> Tuple[str, list]:
    """Парсить данные callback"""
    if ':' not in data:
        return data, []
    
    parts = data.split(':')
    return parts[0], parts[1:]

def is_user_in_chat(context, chat_id: int, user_id: int) -> bool:
    """Проверить, находится ли пользователь в чате"""
    try:
        chat_member = context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False