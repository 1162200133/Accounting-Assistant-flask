import os

# 是否开启debug模式
DEBUG = True

def _env(key: str, default: str):
    """读取环境变量；如果为空字符串/全空白，则回退 default"""
    v = os.environ.get(key)
    return v if v and v.strip() else default

# 读取数据库环境变量
username = _env("MYSQL_USERNAME", "root")
password = _env("MYSQL_PASSWORD", "123456mqY")
db_address = _env("MYSQL_ADDRESS", "sh-cynosdbmysql-grp-azd78c1k.sql.tencentcdb.com:25608")
