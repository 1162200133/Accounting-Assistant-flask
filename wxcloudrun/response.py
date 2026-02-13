# wxcloudrun/response.py
import json
from flask import Response

def make_succ_response(data):
    payload = {'code': 0, 'data': data}
    return Response(json.dumps(payload, ensure_ascii=False), mimetype='application/json')

def make_err_response(err_msg):
    payload = {'code': -1, 'errorMsg': err_msg}
    return Response(json.dumps(payload, ensure_ascii=False), mimetype='application/json')

# ✅ 登录接口专用：匹配前端 data.msg / data.token
def make_login_response(token: str, user: dict, msg: str = '登录成功'):
    payload = {'code': 0, 'msg': msg, 'token': token, 'data': user}
    return Response(json.dumps(payload, ensure_ascii=False), mimetype='application/json')
