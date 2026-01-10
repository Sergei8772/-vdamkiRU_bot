#!/usr/bin/env python3
"""Простой тест работы шашек"""

from game_logic import CheckersGame
from keyboard import create_board_markup

def test_simple():
    print("🧪 Тест простой игры...")
    
    game = CheckersGame()
    
    print("Начальная доска:")
    for i, row in enumerate(game.board):
        print(f"{i}: {' '.join(row)}")
    
    # Проверяем выбор шашки
    print("\n1. Пробуем выбрать шашку (5, 0) - белая:")
    game.selected = (5, 0)
    
    markup = create_board_markup(game, "test123")
    
    print("\nКак выглядит клавиатура:")
    for i, row_buttons in enumerate(markup.inline_keyboard):
        if i < 8:  # только доска
            row_text = ""
            for btn in row_buttons:
                row_text += btn.text + " "
            print(f"Ряд {i}: {row_text}")
    
    print("\n2. Проверяем возможные ходы для шашки (5, 0):")
    moves = game.get_possible_moves(5, 0)
    print(f"Найдено {len(moves)} возможных ходов:")
    for mr, mc, is_cap, _, _ in moves:
        print(f"  -> ({mr}, {mc}) взятие: {is_cap}")

if __name__ == "__main__":
    test_simple()