# wxcloudrun/jwt_utils.py
import os
import jwt
from datetime import datetime, timedelta

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")   # 建议云托管里配置成环境变量
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "30"))

def create_token(payload: dict) -> str:
    data = dict(payload)
    data["iat"] = int(datetime.utcnow().timestamp())
    data["exp"] = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    """
    解码并校验 JWT
    - token 过期/非法会抛异常
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])

