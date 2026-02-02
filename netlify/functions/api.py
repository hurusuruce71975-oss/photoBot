import sys
import os

# Путь к текущей директории
current_dir = os.path.dirname(os.path.abspath(__file__))
# Путь к корню (на два уровня выше)
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))

# Добавляем в sys.path
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Импорт обработчика
from main import handler as app_handler

def handler(event, context):
    return app_handler(event, context)
