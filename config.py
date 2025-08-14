import os

MYSQL_HOST = os.environ.get('DB_HOST', '10.6.250.86')
MYSQL_USER = os.environ.get('DB_USER', 'root')
MYSQL_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
MYSQL_DB = os.environ.get('MYSQL_DB', 'agile_poker')
MYSQL_PORT = int(os.environ.get('DB_PORT', 3306))
