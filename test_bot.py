#!/usr/bin/env python3
"""Тестовый скрипт для проверки работы бота"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_logic import CheckersGame
from ai_engine import CheckersAI

def test_game_logic():
    """Тест логики игры"""
    print("🧪 Тестирование логики игры...")
    
    # Создаем игру
    game = CheckersGame()
    
    print("Доска создана:")
    for row in game.board:
        print(' '.join(row))
    
    # Пробуем сделать ход
    print(f"\nТекущий игрок: {game.current_player}")
    
    # Ищем белую шашку для хода
    white_moves = []
    for row in range(8):
        for col in range(8):
            if (row + col) % 2 == 1 and game.board[row][col] == '⚪':
                moves = game.get_possible_moves(row, col)
                if moves:
                    white_moves.append(((row, col), moves))
    
    if white_moves:
        print(f"Найдено {len(white_moves)} белых шашек с ходами")
        (from_row, from_col), moves = white_moves[0]
        print(f"Шашка на ({from_row}, {from_col}) имеет {len(moves)} возможных ходов")
        
        if moves:
            to_row, to_col, is_capture, _, _ = moves[0]
            print(f"Пробуем ход на ({to_row}, {to_col}), взятие: {is_capture}")
            
            success, message = game.make_move(from_row, from_col, to_row, to_col)
            print(f"Результат: {success}, сообщение: {message}")
            
            if success:
                print("\nДоска после хода:")
                for row in game.board:
                    print(' '.join(row))
                print(f"Новый текущий игрок: {game.current_player}")
    
    # Тест ИИ
    print("\n🧠 Тестирование ИИ...")
    ai = CheckersAI(level="easy", color="BLACK")
    best_move = ai.get_best_move(game)
    
    if best_move:
        (fr, fc), (tr, tc) = best_move
        print(f"ИИ рекомендует ход: с ({fr}, {fc}) на ({tr}, {tc})")
    else:
        print("ИИ не нашел возможных ходов")

if __name__ == "__main__":
    test_game_logic()