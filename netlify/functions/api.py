import sys
import os

# Получаем путь к текущей директории (netlify/functions)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Поднимаемся на два уровня вверх к корню проекта (где лежит main.py)
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))

# Добавляем корень в путь поиска модулей
if root_dir not in sys.path:
    sys.path.append(root_dir)

from main import handler as app_handler

def handler(event, context):
    return app_handler(event, context)
