#!/usr/bin/env python3
"""Отладка работы бота"""

from game_logic import CheckersGame
from ai_engine import BotPlayer

def test_bot_game():
    print("🧪 Тестирование игры с ботом...")
    
    # Создаем игру
    bot_player = BotPlayer(ai_level="easy")
    game = bot_player.setup_game()
    
    print("Начальная доска:")
    for i, row in enumerate(game.board):
        print(f"{i}: {' '.join(row)}")
    
    print(f"\nТекущий игрок: {game.current_player}")
    
    # Пробуем найти белую шашку для хода
    print("\nПоиск белых шашек (игрок)...")
    white_pieces = []
    for row in range(8):
        for col in range(8):
            if (row + col) % 2 == 1 and game.board[row][col] in ['⚪', '⬜']:
                moves = game.get_possible_moves(row, col)
                if moves:
                    white_pieces.append(((row, col), moves))
                    print(f"Шашка на ({row}, {col}) имеет {len(moves)} ходов")
    
    if white_pieces:
        (row, col), moves = white_pieces[0]
        print(f"\nПробуем выбрать шашку на ({row}, {col})")
        
        # Выбираем шашку
        game.selected = (row, col)
        print(f"Шашка выбрана: {game.selected}")
        
        # Показываем возможные ходы
        print(f"Возможные ходы:")
        for mr, mc, is_cap, _, _ in moves:
            print(f"  -> ({mr}, {mc}) взятие: {is_cap}")
        
        if moves:
            to_row, to_col, is_cap, _, _ = moves[0]
            print(f"\nПробуем ход на ({to_row}, {to_col})")
            success, message = bot_player.make_player_move(row, col, to_row, to_col)
            print(f"Результат: {success}, сообщение: {message}")
            
            if success:
                print("\nДоска после хода игрока:")
                for i, row_board in enumerate(game.board):
                    print(f"{i}: {' '.join(row_board)}")
                
                print(f"\nТеперь ходит: {game.current_player}")
                
                # Пробуем ход бота
                print("\n🤖 Ход бота...")
                bot_success, bot_message = bot_player.make_bot_move()
                print(f"Результат бота: {bot_success}, сообщение: {bot_message}")
                
                if bot_success:
                    print("\nДоска после хода бота:")
                    for i, row_board in enumerate(game.board):
                        print(f"{i}: {' '.join(row_board)}")
    else:
        print("Не найдено белых шашек с возможными ходами!")

if __name__ == "__main__":
    test_bot_game()