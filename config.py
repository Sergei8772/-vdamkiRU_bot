import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота
    TOKEN = "8236271877:AAHO2Eb6Lakd3gOsvQoS8PGLPTkVwbQHYMY"
    
    # Настройки базы данных
    DATABASE_PATH = "data/checkers.db"
    
    # Настройки игры
    GAME_TIMEOUT = 300  # 5 минут на игру
    MOVE_TIMEOUT = 120  # 2 минуты на ход
    MAX_GAMES_PER_CHAT = 10  # Максимум игр в одном чате
    
    # Настройки ИИ
    AI_THINKING_TIME = 1.5  # Уменьшено для скорости (0.5 секунды)
    
    # Текстовые константы
    BOT_USERNAME = "@vdamkiRU_bot"
    BOT_NAME = "Шашки vDAMKI"

config = Config()