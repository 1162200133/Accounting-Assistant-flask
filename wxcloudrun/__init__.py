from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pymysql
import config
import os

pymysql.install_as_MySQLdb()

app = Flask(__name__, instance_relative_config=True)
app.config['DEBUG'] = config.DEBUG


def _env(v, default):
    return v if v and str(v).strip() else default


# 空值兜底（关键）
username = _env(config.username, "root")
password = _env(config.password, "123456mqY")
db_address = _env(config.db_address, "sh-cynosdbmysql-grp-azd78c1k.sql.tencentcdb.com:25608")

# 明确使用 pymysql
app.config['SQLALCHEMY_DATABASE_URI'] = \
    f'mysql+pymysql://{username}:{password}@{db_address}/accounting_mp?charset=utf8mb4'

print(">>> DB ADDRESS:", db_address)
print(">>> DB URI:", app.config['SQLALCHEMY_DATABASE_URI'].replace(password, "****"))

db = SQLAlchemy(app)

from wxcloudrun import views
app.config.from_object('config')
