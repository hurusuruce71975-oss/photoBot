import sys
import os

# Добавляем корень проекта в путь, чтобы найти main.py
# В среде Lambda/Netlify файлы распаковываются, и корень часто доступен.
# Иногда нужно явно добавить путь.
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.append(root)
    
# А также родителя, если api.py лежит в подпапке
parent = os.path.dirname(root)
if parent not in sys.path:
    sys.path.append(parent)

from main import handler as app_handler

def handler(event, context):
    return app_handler(event, context)
