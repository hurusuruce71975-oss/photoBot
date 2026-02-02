import sys
import os

# Добавляем родительскую директорию в путь поиска модулей, 
# чтобы можно было импортировать main.py и остальные файлы из корня.
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from main import handler as app_handler

def handler(event, context):
    return app_handler(event, context)
