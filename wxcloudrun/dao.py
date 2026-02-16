# wxcloudrun/dao.py
from datetime import datetime, timedelta
from wxcloudrun import db
from wxcloudrun.model import User, Category, Record,Receipt
from sqlalchemy import func, case

def add_record_with_receipts(user_id: str, type: str, amount_cent: int, category_id: int,
                             occur_at: str, note=None, category_name_snapshot=None,
                             receipts=None):
    """
    receipts: list[dict] like:
      [{"file_id":"cloud://xxx", "mime_type":"image/jpeg", "size_bytes":12345, "file_url":None}, ...]
    """
    dt = _parse_dt(occur_at)

    r = Record(
        user_id=user_id,
        type=type,
        amount_cent=amount_cent,
        category_id=category_id,
        category_name_snapshot=category_name_snapshot,
        note=note,
        occur_at=dt,
    )

    db.session.add(r)
    db.session.flush()  # ✅ 拿到 r.id，但不提交

    recs = receipts or []
    for it in recs:
        file_id = (it.get("file_id") or "").strip()
        if not file_id:
            continue
        db.session.add(Receipt(
            record_id=r.id,
            user_id=user_id,
            file_id=file_id,
            mime_type=it.get("mime_type"),
            size_bytes=it.get("size_bytes"),
        ))

    db.session.commit()
    return r


def count_records_by_category(user_id: str, cid: int) -> int:
    return Record.query.filter_by(user_id=user_id, category_id=cid).count()

def sync_records_for_category(user_id: str, cid: int, new_name: str = None, new_type: str = None) -> int:
    """
    同步更新所有引用该分类的记录：
    - category_name_snapshot 同步为 new_name
    - type 同步为 new_type（可选，建议在分类 type 变更时同步，避免详情页按 type 拉分类找不到）
    返回：影响行数
    """
    update_fields = {}
    if new_name is not None:
        update_fields["category_name_snapshot"] = new_name
    if new_type is not None:
        if new_type not in ("income", "expense"):
            raise ValueError("new_type 只能是 income 或 expense")
        update_fields["type"] = new_type

    if not update_fields:
        return 0

    n = Record.query.filter_by(user_id=user_id, category_id=cid).update(
        update_fields, synchronize_session=False
    )
    db.session.commit()
    return int(n or 0)

def get_record_by_id(user_id: str, rid: int, include_hidden: bool = False):
    q = Record.query.filter_by(user_id=user_id, id=rid)
    if not include_hidden:
        q = q.filter_by(is_hidden=0)
    return q.first()


def update_record(user_id: str, rid: int, **fields):
    r = get_record_by_id(user_id, rid)
    if not r:
        raise ValueError("记录不存在")

    allow = {"type", "amount_cent", "category_id", "note", "occur_at", "category_name_snapshot"}
    for k, v in fields.items():
        if k in allow and v is not None:
            setattr(r, k, v)

    db.session.commit()
    return r

def delete_record(user_id: str, rid: int):
    r = get_record_by_id(user_id, rid)
    if not r:
        raise ValueError("记录不存在")

    # ✅ 软删除：仅隐藏
    r.is_hidden = 1
    db.session.commit()
    return True

def restore_record(user_id: str, rid: int):
    """
    恢复被隐藏(软删除)的记录：is_hidden=0
    """
    r = Record.query.filter_by(user_id=user_id, id=rid).first()
    if not r:
        raise ValueError("记录不存在")

    # 如果你后面把 get_record_by_id 默认过滤 is_hidden=0，这里要单独查全量，所以直接 query
    r.is_hidden = 0
    db.session.commit()
    return r


def add_category(user_id: str, type_: str, name: str, icon=None, color=None, sort: int = 0, is_hidden: int = 0):
    """
    新增分类（同一用户下 user_id + type + name 唯一）
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("分类名称不能为空")

    if type_ not in ("income", "expense"):
        raise ValueError("type 只能是 income 或 expense")

    existed = Category.query.filter_by(user_id=user_id, type=type_, name=name).first()
    if existed:
        raise ValueError("该分类已存在")

    c = Category(
        user_id=user_id,
        type=type_,
        name=name,
        icon=icon,
        color=color,
        sort=int(sort or 0),
        is_hidden=int(is_hidden or 0),
        is_preset=0
    )
    db.session.add(c)
    db.session.commit()
    return c

def get_category(user_id: str, cid: int) -> Category:
    c = Category.query.filter_by(id=cid, user_id=user_id).first()
    if not c:
        raise ValueError("分类不存在")
    return c

def update_category(user_id, cid, type_=None, name=None, icon=None, color=None, sort=None, is_hidden=None):
    c = Category.query.filter_by(user_id=user_id, id=cid).first()
    if not c:
        raise Exception("分类不存在")

    # type 更新（只允许 income / expense）
    if type_ is not None:
        if type_ not in ("income", "expense"):
            raise Exception("type 只能是 income/expense")
        c.type = type_

    if name is not None:
        c.name = name
    if icon is not None:
        c.icon = icon
    if color is not None:
        c.color = color
    if sort is not None:
        c.sort = int(sort)
    if is_hidden is not None:
        c.is_hidden = int(is_hidden)

    db.session.commit()
    return c


def delete_category(user_id: str, cid: int):
    c = get_category(user_id, cid)
    # 预置分类：不允许删除（建议隐藏）
    if int(getattr(c, "is_preset", 0) or 0) == 1:
        raise ValueError("预置分类不允许删除，可选择隐藏")
    # 软删除：改为隐藏，避免历史记录 category_id 失效
    c.is_hidden = 1
    db.session.commit()

def get_or_create_user_by_openid(openid: str, nick_name=None, avatar_url=None) -> User:
    u = User.query.filter_by(user_id=openid).first()
    if u:
        # 可选：更新昵称头像
        changed = False
        if nick_name and u.nick_name != nick_name:
            u.nick_name = nick_name
            changed = True
        if avatar_url and u.avatar_url != avatar_url:
            u.avatar_url = avatar_url
            changed = True
        if changed:
            db.session.commit()

        # ✅ 关键：老用户如果没有分类，也补一份默认分类
        has_any = Category.query.filter_by(user_id=openid).first()
        if not has_any:
            seed_default_categories(openid)

        return u

    # 新用户创建
    u = User(user_id=openid, nick_name=nick_name, avatar_url=avatar_url)
    db.session.add(u)
    db.session.commit()

    # 新用户创建一份预置分类
    seed_default_categories(openid)
    return u


def seed_default_categories(user_id: str):
    # ✅ 预置分类：补上默认颜色（你可以按自己UI风格调整）
    presets = [
        # expense
        ("expense", "餐饮", "food",     "#FF8A00", 100),
        ("expense", "交通", "traffic",  "#2D7CFF", 90),
        ("expense", "购物", "shopping", "#FF4D4F", 80),
        ("expense", "住房", "house",    "#8B5CF6", 70),
        # income
        ("income",  "工资", "salary",   "#34C759", 100),
        ("income",  "奖金", "bonus",    "#10B981", 90),
    ]

    changed = False

    for t, name, icon, color, sort in presets:
        existed = Category.query.filter_by(user_id=user_id, type=t, name=name).first()

        if existed:
            # ✅ 老用户：如果预置分类颜色为空，补齐（不覆盖用户自己设置过的颜色）
            if (not getattr(existed, "color", None)) and color:
                existed.color = color
                changed = True
            # 可选：icon 为空也补一下
            if (not getattr(existed, "icon", None)) and icon:
                existed.icon = icon
                changed = True
            # sort 为 0 时补一下（不强制覆盖）
            if (getattr(existed, "sort", 0) or 0) == 0 and sort:
                existed.sort = sort
                changed = True
            continue

        
        db.session.add(Category(
            user_id=user_id,
            type=t,
            name=name,
            icon=icon,
            color=color,     
            is_hidden=0,
            sort=sort,
            is_preset=1
        ))
        changed = True

    if changed:
        db.session.commit()



def list_categories(user_id: str, type_=None, include_hidden=False):
    q = Category.query.filter_by(user_id=user_id)
    if type_ in ("income", "expense"):
        q = q.filter_by(type=type_)
    if not include_hidden:
        q = q.filter_by(is_hidden=0)
    return q.order_by(Category.sort.desc(), Category.id.desc()).all()


def add_record(user_id: str, type: str, amount_cent: int, category_id: int,
               occur_at: str, note=None, category_name_snapshot=None):
    # occur_at 支持 "YYYY-MM-DD HH:MM:SS" 或 ISO
    dt = _parse_dt(occur_at)

    r = Record(
        user_id=user_id,
        type=type,
        amount_cent=amount_cent,
        category_id=category_id,
        category_name_snapshot=category_name_snapshot,
        note=note,
        occur_at=dt,
    )
    db.session.add(r)
    db.session.commit()
    return r


from datetime import datetime, timedelta

def list_records(user_id: str, month: str = None, day: str = None,
                 page: int = 1, page_size: int = 20,
                 only_hidden: bool = False):
    """
    返回：items, total
    items: [(Record, category_color), ...]
    """
    q = db.session.query(
        Record,
        Category.color.label("category_color")
    ).outerjoin(
        Category,
        (Category.id == Record.category_id) & (Category.user_id == user_id)
    ).filter(Record.user_id == user_id)

    # ✅ 回收站 / 正常列表
    q = q.filter(Record.is_hidden == (1 if only_hidden else 0))

    # ✅ 日期过滤
    if day:
        start = datetime.strptime(day, "%Y-%m-%d")
        end = start.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        q = q.filter(Record.occur_at >= start, Record.occur_at < end)
    elif month:
        start = datetime.strptime(month + "-01", "%Y-%m-%d")
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)
        q = q.filter(Record.occur_at >= start, Record.occur_at < end)

    q = q.order_by(Record.occur_at.desc(), Record.id.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def calendar_summary(user_id: str, month: str):
    """
    返回当月每天的收入/支出汇总，用于日历标记
    """
    from sqlalchemy import func, case

    start = datetime.strptime(month + "-01", "%Y-%m-%d")
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    rows = db.session.query(
        func.date(Record.occur_at).label("d"),
        func.count(Record.id).label("cnt"),
        func.sum(case((Record.type == "income", Record.amount_cent), else_=0)).label("income"),
        func.sum(case((Record.type == "expense", Record.amount_cent), else_=0)).label("expense"),
    ).filter(
        Record.is_hidden == 0,
        Record.user_id == user_id,
        Record.occur_at >= start,
        Record.occur_at < end
    ).group_by(func.date(Record.occur_at)).all()

    out = []
    for r in rows:
        out.append({
            "day": r.d.strftime("%Y-%m-%d"),
            "count": int(r.cnt or 0),
            "income_cent": int(r.income or 0),
            "expense_cent": int(r.expense or 0),
        })
    return {"month": month, "days": out}

def day_summary(user_id: str, day: str):
    """
    返回某天收入/支出汇总（单位：cent）
    """
    start = datetime.strptime(day, "%Y-%m-%d")
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    row = db.session.query(
        func.count(Record.id).label("cnt"),
        func.sum(case((Record.type == "income", Record.amount_cent), else_=0)).label("income"),
        func.sum(case((Record.type == "expense", Record.amount_cent), else_=0)).label("expense"),
    ).filter(
        Record.is_hidden == 0,
        Record.user_id == user_id,
        Record.occur_at >= start,
        Record.occur_at < end
    ).first()

    cnt = int(row.cnt or 0)
    income = int(row.income or 0)
    expense = int(row.expense or 0)
    return {
        "day": day,
        "count": cnt,
        "income_cent": income,
        "expense_cent": expense,
        "net_cent": income - expense
    }
    
def month_summary(user_id: str, month: str):
    # 返回当月收入/支出汇总（分）
    from sqlalchemy import func, case
    start = datetime.strptime(month + "-01", "%Y-%m-%d")
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)

    row = db.session.query(
        func.sum(case((Record.type == "income", Record.amount_cent), else_=0)).label("income"),
        func.sum(case((Record.type == "expense", Record.amount_cent), else_=0)).label("expense"),
    ).filter(
        Record.is_hidden == 0,
        Record.user_id == user_id,
        Record.occur_at >= start,
        Record.occur_at < end
    ).first()

    income = int(row.income or 0)
    expense = int(row.expense or 0)
    return {"month": month, "income_cent": income, "expense_cent": expense, "balance_cent": income - expense}


def _parse_dt(s: str) -> datetime:
    s = (s or "").strip()
    # 兼容 "2026-02-13 12:00:00"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    # 兼容 "2026-02-13"
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        pass
    # 兼容 ISO
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        raise ValueError("occur_at 格式不正确")
