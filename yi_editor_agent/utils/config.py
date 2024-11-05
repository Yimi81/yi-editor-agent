import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_PATH = os.path.join(BASE_DIR, 'output')
LOG_PATH = os.path.join(BASE_DIR, 'logs')
DATA_PATH = os.path.join(BASE_DIR, 'data')
VECTOR_DB_PATH = os.path.join(BASE_DIR, 'vector_db')


# 确保输出路径和日志路径存在
os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True)
os.makedirs(DATA_PATH, exist_ok=True)
os.makedirs(VECTOR_DB_PATH, exist_ok=True)