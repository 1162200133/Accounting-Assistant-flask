# wxcloudrun/views.py
import os
import requests
from flask import request
from run import app
from wxcloudrun.response import make_succ_response, make_err_response, make_login_response
from wxcloudrun.dao import get_or_create_user, list_categories, add_record
from wxcloudrun.dao import get_or_create_user_by_openid
from wxcloudrun.jwt_utils import create_token,decode_token
from wxcloudrun.model import User 

WX_APPID = os.getenv('WX_APPID', 'wxf2ad56f65cb79fee')
WX_SECRET = os.getenv('WX_SECRET', '8eda8e66f289fe0fc3dbd36919b3fb28')

@app.route('/api/categories', methods=['GET'])
def categories_get():
    user_id = request.args.get('user_id')
    if not user_id:
        return make_err_response('缺少 user_id')
    type_ = request.args.get('type')  # income/expense/None
    items = list_categories(user_id, type_=type_, include_hidden=False)
    data = [{
        'id': c.id, 'type': c.type, 'name': c.name, 'icon': c.icon,
        'is_hidden': c.is_hidden, 'sort': c.sort
    } for c in items]
    return make_succ_response(data)

@app.route('/api/records', methods=['POST'])
def records_add():
    params = request.get_json() or {}
    required = ['user_id', 'type', 'amount_cent', 'category_id', 'occur_at']
    for k in required:
        if k not in params:
            return make_err_response(f'缺少 {k}')
    r = add_record(
        user_id=params['user_id'],
        type=params['type'],
        amount_cent=int(params['amount_cent']),
        category_id=int(params['category_id']),
        note=params.get('note'),
        occur_at=params['occur_at'],  # 你可以前端传 ISO 字符串，后端再 parse
        category_name_snapshot=params.get('category_name_snapshot'),
    )
    return make_succ_response({'id': r.id})

@app.route('/api/wxlogin', methods=['POST'])
def wxlogin():
    params = request.get_json() or {}
    code = params.get('code')
    nick_name = params.get('nickName') or params.get('nick_name')
    avatar_url = params.get('avatarUrl') or params.get('avatar_url')

    if not code:
        return make_err_response('缺少code')
    if not WX_APPID or not WX_SECRET:
        return make_err_response('服务端未配置WX_APPID/WX_SECRET')

    # code -> openid
    resp = requests.get(
        'https://api.weixin.qq.com/sns/jscode2session',
        params={
            'appid': WX_APPID,
            'secret': WX_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        },
        timeout=8
    )
    data = resp.json() if resp is not None else {}
    openid = data.get('openid')
    if not openid:
        return make_err_response(f"微信登录失败：{data.get('errmsg') or '未获取到openid'}")

    # 查/建用户
    u = get_or_create_user_by_openid(openid, nick_name=nick_name, avatar_url=avatar_url)

    # 签发JWT（前端 jwtDecode(token) 会拿到这些字段）
    token = create_token({
        "user_id": u.user_id,
        "nick_name": u.nick_name,
        "avatar_url": u.avatar_url,
        "login_type": "wx"
    })

    return make_login_response(token, {
        "user_id": u.user_id,
        "nick_name": u.nick_name,
        "avatar_url": u.avatar_url,
        "login_type": "wx"
    }, msg='登录成功')
    
def _get_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()

    t = request.headers.get("token")  # 兼容你 app.js 可能用 token 头
    if t:
        return t.strip()

    t = request.args.get("token")
    if t:
        return t.strip()

    return ""

@app.route('/api/whoami', methods=['GET'])
def whoami():
    token = _get_token()
    if not token:
        return make_err_response("未登录：缺少token")

    try:
        payload = decode_token(token)
    except Exception:
        return make_err_response("token无效或已过期")

    user_id = payload.get("user_id")
    login_type = payload.get("login_type") or "wx"

    if not user_id:
        return make_err_response("token缺少user_id")

    # 查 users 表
    u = User.query.filter_by(user_id=user_id).first()
    if not u:
        return make_err_response("用户不存在，请重新登录")

    data = {
        "login_type": login_type,
        "user_id": u.user_id,
        "openid": u.user_id if login_type == "wx" else "",
        "nick_name": u.nick_name,
        "avatar_url": u.avatar_url,
        "currency": u.currency,
        "status": u.status,
        "phone": u.phone,
        "email": u.email,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else None,
        "updated_at": u.updated_at.strftime("%Y-%m-%d %H:%M:%S") if u.updated_at else None,
    }
    return make_succ_response(data)
