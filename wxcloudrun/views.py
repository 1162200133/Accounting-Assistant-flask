# wxcloudrun/views.py
import os
import requests
from flask import request
from run import app
from wxcloudrun.response import make_succ_response, make_err_response, make_login_response
from wxcloudrun.jwt_utils import create_token,decode_token
from wxcloudrun.model import User 

from wxcloudrun.dao import (
    calendar_summary,
    day_summary,
    delete_record,
    get_or_create_user_by_openid,
    get_record_by_id,
    list_categories,
    add_record,
    add_category, 
    list_records,
    month_summary,
    seed_default_categories,
    update_record
)


WX_APPID = os.getenv('WX_APPID', 'wxf2ad56f65cb79fee')
WX_SECRET = os.getenv('WX_SECRET', '8eda8e66f289fe0fc3dbd36919b3fb28')

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

def _current_user_id():
    token = _get_token()
    if not token:
        return None, "未登录：缺少token"
    try:
        payload = decode_token(token)
    except Exception:
        return None, "token无效或已过期"
    uid = payload.get("user_id")
    if not uid:
        return None, "token缺少user_id"
    return uid, None


@app.route('/api/categories', methods=['GET'])
def categories_get():
    # ✅ 从 token 取当前用户
    token = _get_token()
    if not token:
        return make_err_response("未登录：缺少token")

    try:
        payload = decode_token(token)
    except Exception:
        return make_err_response("token无效或已过期")

    user_id = payload.get("user_id")
    if not user_id:
        return make_err_response("token缺少user_id")

    # 参数：income/expense/None
    type_ = request.args.get('type')

    # ✅ 查分类
    items = list_categories(user_id, type_=type_, include_hidden=False)

    # ✅ 如果没有分类，自动补齐（老用户也能恢复）
    if not items:
        seed_default_categories(user_id)
        items = list_categories(user_id, type_=type_, include_hidden=False)

    data = [{
        'id': c.id,
        'type': c.type,
        'name': c.name,
        'icon': c.icon,
        'color': getattr(c, 'color', None),
        'is_hidden': c.is_hidden,
        'sort': c.sort
    } for c in items]

    return make_succ_response(data)

@app.route('/api/categories', methods=['POST'])
def categories_add():
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    params = request.get_json() or {}
    type_ = params.get("type")
    name = params.get("name")
    icon = params.get("icon")
    color = params.get("color")
    sort = params.get("sort", 0)
    is_hidden = params.get("is_hidden", 0)

    if not type_:
        return make_err_response("缺少 type（income/expense）")
    if not name:
        return make_err_response("缺少 name（分类名称）")

    try:
        c = add_category(
            user_id=user_id,
            type_=type_,
            name=name,
            icon=icon,
            color=color,
            sort=sort,
            is_hidden=is_hidden
        )
    except Exception as e:
        return make_err_response(str(e))

    return make_succ_response({
        "id": c.id,
        "type": c.type,
        "name": c.name,
        "icon": c.icon,
        "color": getattr(c, "color", None),
        "is_hidden": c.is_hidden,
        "sort": c.sort
    })

@app.route('/api/records', methods=['POST'])
def records_add():
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    params = request.get_json() or {}
    required = ['type', 'amount_cent', 'category_id', 'occur_at']
    for k in required:
        if k not in params:
            return make_err_response(f'缺少 {k}')

    r = add_record(
        user_id=user_id,
        type=params['type'],
        amount_cent=int(params['amount_cent']),
        category_id=int(params['category_id']),
        note=params.get('note'),
        occur_at=params['occur_at'],
        category_name_snapshot=params.get('category_name_snapshot'),
    )
    return make_succ_response({'id': r.id})

@app.route('/api/records', methods=['GET'])
def records_list():
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    month = request.args.get("month")  # "YYYY-MM"
    day = request.args.get("day")  # "YYYY-MM-DD"
    page = int(request.args.get("page", "1"))
    page_size = int(request.args.get("page_size", "20"))

    items, total = list_records(user_id, month=month, day=day, page=page, page_size=page_size)
    data = []
    for r in items:
        data.append({
            "id": r.id,
            "type": r.type,
            "amount_cent": r.amount_cent,
            "category_id": r.category_id,
            "category_name_snapshot": r.category_name_snapshot,
            "note": r.note,
            "occur_at": r.occur_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return make_succ_response({"items": data, "total": total, "page": page, "page_size": page_size})

@app.route('/api/records/<int:rid>', methods=['GET'])
def record_detail(rid):
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    r = get_record_by_id(user_id, rid)
    if not r:
        return make_err_response("记录不存在")

    return make_succ_response({
        "id": r.id,
        "type": r.type,
        "amount_cent": r.amount_cent,
        "category_id": r.category_id,
        "category_name_snapshot": r.category_name_snapshot,
        "note": r.note or "",
        "occur_at": r.occur_at.strftime("%Y-%m-%d %H:%M:%S"),
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(r, "created_at", None) else None,
        "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(r, "updated_at", None) else None,
    })

@app.route('/api/records/<int:rid>', methods=['PUT'])
def record_update(rid):
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    params = request.get_json() or {}

    # 可改字段：type / amount_cent / category_id / note / occur_at / category_name_snapshot
    try:
        r = update_record(
            user_id, rid,
            type=params.get("type"),
            amount_cent=int(params["amount_cent"]) if "amount_cent" in params else None,
            category_id=int(params["category_id"]) if "category_id" in params else None,
            note=params.get("note"),
            occur_at=params.get("occur_at"),
            category_name_snapshot=params.get("category_name_snapshot"),
        )
    except Exception as e:
        return make_err_response(str(e))

    return make_succ_response({"id": r.id})

@app.route('/api/records/<int:rid>', methods=['DELETE'])
def record_delete(rid):
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    try:
        delete_record(user_id, rid)
    except Exception as e:
        return make_err_response(str(e))

    return make_succ_response({"id": rid})

@app.route('/api/stats/calendar', methods=['GET'])
def stats_calendar():
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    month = request.args.get("month")
    if not month:
        return make_err_response("缺少 month，格式 YYYY-MM")

    return make_succ_response(calendar_summary(user_id, month))

@app.route('/api/stats/month', methods=['GET'])
def stats_month():
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    month = request.args.get("month")
    if not month:
        return make_err_response("缺少 month，格式 YYYY-MM")

    return make_succ_response(month_summary(user_id, month))

@app.route('/api/stats/day', methods=['GET'])
def stats_day():
    user_id, err = _current_user_id()
    if err:
        return make_err_response(err)

    day = request.args.get("day")
    if not day:
        return make_err_response("缺少 day，格式 YYYY-MM-DD")

    return make_succ_response(day_summary(user_id, day))

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
    s = requests.Session()
    s.trust_env = False # 避免走代理（如果服务器环境配置了 http_proxy 之类的环境变量）
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
    
@app.route('/api/logout', methods=['POST'])
def logout():
    """
    JWT 是无状态的，前端删除 token 即可视为退出。
    这里做一次 token 校验，仅用于返回统一格式。
    """
    token = _get_token()
    if not token:
        # 没 token 也算成功（已经退出）
        return make_succ_response({"msg": "已退出登录"})

    try:
        decode_token(token)
    except Exception:
        # token 无效也视为已退出
        return make_succ_response({"msg": "已退出登录"})

    return make_succ_response({"msg": "已退出登录"})

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
