import sys
import os

# Текущая директория: netlify/functions/api
current_dir = os.path.dirname(os.path.abspath(__file__))
# Корень проекта: ../../../ (три уровня вверх)
root_dir = os.path.abspath(os.path.join(current_dir, "../../../"))

# Добавляем корень в sys.path
if root_dir not in sys.path:
    sys.path.append(root_dir)

from main import handler as app_handler

def handler(event, context):
    return app_handler(event, context)