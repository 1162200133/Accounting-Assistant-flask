# wxcloudrun/dao.py
from wxcloudrun import db
from wxcloudrun.model import User, Category, Record, Budget

def get_or_create_user(user_id, nick_name=None, avatar_url=None):
    u = User.query.filter_by(user_id=user_id).first()
    if u:
        return u
    u = User(user_id=user_id, nick_name=nick_name, avatar_url=avatar_url)
    db.session.add(u)
    db.session.commit()
    return u

def list_categories(user_id, type_=None, include_hidden=False):
    q = Category.query.filter_by(user_id=user_id)
    if type_:
        q = q.filter_by(type=type_)
    if not include_hidden:
        q = q.filter_by(is_hidden=0)
    return q.order_by(Category.sort.desc(), Category.id.desc()).all()

def add_record(**kwargs):
    r = Record(**kwargs)
    db.session.add(r)
    db.session.commit()
    return r


def get_or_create_user_by_openid(openid: str, nick_name: str = None, avatar_url: str = None) -> User:
    u = User.query.filter_by(user_id=openid).first()
    if u:
        # 可选：同步昵称头像
        changed = False
        if nick_name and u.nick_name != nick_name:
            u.nick_name = nick_name
            changed = True
        if avatar_url and u.avatar_url != avatar_url:
            u.avatar_url = avatar_url
            changed = True
        if changed:
            db.session.commit()
        return u

    u = User(user_id=openid, nick_name=nick_name, avatar_url=avatar_url)
    db.session.add(u)
    db.session.commit()
    return u