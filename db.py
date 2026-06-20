# -*- coding: utf-8 -*-
"""
طبقة قاعدة البيانات لتطبيق الكاشير وإدارة المخزون (نسخة الويب)
SQLite + sqlite3 القياسية بدون أي اعتمادية خارجية لقاعدة البيانات
"""
import sqlite3
import os
import shutil
import hashlib
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "shop.db")


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'employee',
        active INTEGER DEFAULT 1,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT,
        details TEXT,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        barcode TEXT UNIQUE,
        category_id INTEGER,
        purchase_price REAL DEFAULT 0,
        sale_price REAL DEFAULT 0,
        quantity REAL DEFAULT 0,
        min_quantity REAL DEFAULT 2,
        image_path TEXT,
        created_at TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        phone TEXT,
        notes TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE,
        date TEXT,
        customer_name TEXT,
        subtotal REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        profit REAL DEFAULT 0,
        notes TEXT,
        user_id INTEGER,
        username TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        item_id INTEGER,
        item_name TEXT,
        quantity REAL,
        price REAL,
        purchase_price REAL DEFAULT 0,
        total REAL,
        profit REAL DEFAULT 0,
        FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE SET NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT,
        date TEXT,
        supplier_id INTEGER,
        total REAL DEFAULT 0,
        notes TEXT,
        user_id INTEGER,
        username TEXT,
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER,
        item_id INTEGER,
        item_name TEXT,
        quantity REAL,
        purchase_price REAL,
        total REAL,
        FOREIGN KEY(purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
        FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE SET NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS expense_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        type_id INTEGER,
        amount REAL,
        notes TEXT,
        user_id INTEGER,
        username TEXT,
        FOREIGN KEY(type_id) REFERENCES expense_types(id) ON DELETE SET NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory_counts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        notes TEXT,
        user_id INTEGER,
        username TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory_count_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        count_id INTEGER,
        item_id INTEGER,
        item_name TEXT,
        system_qty REAL,
        actual_qty REAL,
        diff REAL,
        FOREIGN KEY(count_id) REFERENCES inventory_counts(id) ON DELETE CASCADE,
        FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE SET NULL
    )""")

    # الخزنة: سجل حركات نقدية (وارد/منصرف) - يغذى تلقائياً من المبيعات والمشتريات والمصاريف
    c.execute("""CREATE TABLE IF NOT EXISTS treasury_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        type TEXT,            -- 'in' or 'out'
        source TEXT,          -- sale / purchase / expense / manual_deposit / manual_withdraw
        ref_id INTEGER,
        amount REAL,
        notes TEXT,
        user_id INTEGER,
        username TEXT
    )""")

    conn.commit()
    seed_defaults(conn)
    conn.close()


def seed_defaults(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, full_name, role, active, created_at) VALUES (?,?,?,?,?,?)",
                   ("admin", hash_password("admin1234"), "مدير النظام", "admin", 1, now_str()))

    defaults = {
        "shop_name": "محل الهدايا والإكسسوارات",
        "shop_logo": "",
        "theme_mode": "light",
        "primary_color": "#6C5CE7",
        "accent_color": "#00CEC9",
        "currency": "ج.م",
        "invoice_prefix": "INV",
        "last_backup": "",
        # تخصيص شاشة تسجيل الدخول
        "login_template": "classic",
        "login_bg": "",
        "login_logo": "",
        "login_logo_size": "90",
        "login_logo_position": "top",
        "login_show_logo": "1",
        "login_app_name": "محل الهدايا والإكسسوارات",
        "login_welcome": "مرحباً بك، سجّل الدخول لإدارة المحل",
        "login_bg_color": "#6C5CE7",
        "login_button_style": "rounded",
        "login_input_style": "rounded",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (k, v))

    for cat in ["هدايا", "إكسسوارات", "ميك أب", "عطور", "متنوع"]:
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))

    for t in ["إيجار", "كهرباء", "رواتب", "نقل وتوصيل", "صيانة", "متنوع"]:
        c.execute("INSERT OR IGNORE INTO expense_types (name) VALUES (?)", (t,))

    conn.commit()


# =====================================================================
# دوال مساعدة عامة
# =====================================================================
def query_all(query, params=()):
    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_one(query, params=()):
    conn = get_conn()
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None


def execute(query, params=()):
    conn = get_conn()
    cur = conn.execute(query, params)
    conn.commit()
    lastrowid = cur.lastrowid
    conn.close()
    return lastrowid


def execute_many(statements):
    """statements: list of (query, params) تُنفذ كلها داخل معاملة واحدة"""
    conn = get_conn()
    try:
        for q, p in statements:
            conn.execute(q, p)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =====================================================================
# سجل النشاط
# =====================================================================
def log_activity(user, action, details=""):
    user_id = user.get("id") if user else None
    username = user.get("username") if user else "غير معروف"
    execute("INSERT INTO activity_log (user_id, username, action, details, created_at) VALUES (?,?,?,?,?)",
            (user_id, username, action, details, now_str()))


def get_activity_log(search="", limit=500):
    q = "SELECT * FROM activity_log WHERE 1=1"
    params = []
    if search:
        q += " AND (username LIKE ? OR action LIKE ? OR details LIKE ?)"
        params += [f"%{search}%"] * 3
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return query_all(q, params)


# =====================================================================
# المستخدمون
# =====================================================================
def get_user_by_username(username):
    return query_one("SELECT * FROM users WHERE username=?", (username,))


def get_user_by_id(uid):
    return query_one("SELECT * FROM users WHERE id=?", (uid,))


def check_login(username, password):
    user = get_user_by_username(username)
    if user and user["active"] and user["password"] == hash_password(password):
        return user
    return None


def get_users():
    return query_all("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id")


def add_user(username, password, full_name, role):
    return execute("INSERT INTO users (username, password, full_name, role, active, created_at) VALUES (?,?,?,?,1,?)",
                    (username, hash_password(password), full_name, role, now_str()))


def update_user(uid, full_name, role, active):
    execute("UPDATE users SET full_name=?, role=?, active=? WHERE id=?", (full_name, role, active, uid))


def update_user_password(uid, new_password):
    execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_password), uid))


def delete_user(uid):
    execute("DELETE FROM users WHERE id=?", (uid,))


# =====================================================================
# الإعدادات
# =====================================================================
def get_setting(key, default=""):
    row = query_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key, value):
    execute("INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def get_all_settings():
    rows = query_all("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


def set_many_settings(d):
    for k, v in d.items():
        set_setting(k, v)


# =====================================================================
# الأقسام
# =====================================================================
def get_categories():
    return query_all("SELECT * FROM categories ORDER BY name")


def get_category_by_name(name):
    return query_one("SELECT * FROM categories WHERE name=?", (name,))


def add_category(name):
    return execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))


def get_or_create_category(name):
    if not name:
        return None
    row = get_category_by_name(name)
    if row:
        return row["id"]
    return execute("INSERT INTO categories (name) VALUES (?)", (name,))


def update_category(cat_id, name):
    execute("UPDATE categories SET name=? WHERE id=?", (name, cat_id))


def delete_category(cat_id):
    execute("DELETE FROM categories WHERE id=?", (cat_id,))


# =====================================================================
# الأصناف
# =====================================================================
def get_items(search="", category_id=None):
    q = """SELECT items.*, categories.name as category_name
           FROM items LEFT JOIN categories ON items.category_id = categories.id WHERE 1=1"""
    params = []
    if search:
        q += " AND (items.name LIKE ? OR items.barcode LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category_id:
        q += " AND items.category_id = ?"
        params.append(category_id)
    q += " ORDER BY items.id DESC"
    return query_all(q, params)


def get_item(item_id):
    return query_one("""SELECT items.*, categories.name as category_name FROM items
                         LEFT JOIN categories ON items.category_id = categories.id WHERE items.id=?""", (item_id,))


def get_item_by_barcode(barcode):
    return query_one("SELECT * FROM items WHERE barcode=?", (barcode,))


def get_item_by_name(name):
    return query_one("SELECT * FROM items WHERE name=?", (name,))


def add_item(name, barcode, category_id, purchase_price, sale_price, quantity, min_quantity, image_path=""):
    return execute("""INSERT INTO items (name, barcode, category_id, purchase_price, sale_price, quantity,
                       min_quantity, image_path, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (name, barcode or None, category_id, purchase_price, sale_price, quantity, min_quantity,
                     image_path, now_str()))


def update_item(item_id, name, barcode, category_id, purchase_price, sale_price, quantity, min_quantity, image_path=None):
    if image_path is None:
        execute("""UPDATE items SET name=?, barcode=?, category_id=?, purchase_price=?, sale_price=?,
                   quantity=?, min_quantity=? WHERE id=?""",
                (name, barcode or None, category_id, purchase_price, sale_price, quantity, min_quantity, item_id))
    else:
        execute("""UPDATE items SET name=?, barcode=?, category_id=?, purchase_price=?, sale_price=?,
                   quantity=?, min_quantity=?, image_path=? WHERE id=?""",
                (name, barcode or None, category_id, purchase_price, sale_price, quantity, min_quantity,
                 image_path, item_id))


def delete_item(item_id):
    execute("DELETE FROM items WHERE id=?", (item_id,))


def adjust_item_quantity(item_id, delta):
    execute("UPDATE items SET quantity = quantity + ? WHERE id=?", (delta, item_id))


def set_item_quantity(item_id, qty):
    execute("UPDATE items SET quantity=? WHERE id=?", (qty, item_id))


def get_low_stock_items():
    return query_all("SELECT * FROM items WHERE quantity <= min_quantity ORDER BY quantity ASC")


def count_items():
    return query_one("SELECT COUNT(*) as c FROM items")["c"]


def upsert_item_by_name_or_barcode(name, barcode, category_name, purchase_price, sale_price, quantity, min_quantity):
    """تستخدم في الاستيراد من Excel: تحديث الصنف إن وجد بنفس الباركود أو الاسم، أو إضافته جديداً"""
    existing = None
    if barcode:
        existing = get_item_by_barcode(barcode)
    if not existing and name:
        existing = get_item_by_name(name)
    category_id = get_or_create_category(category_name) if category_name else None
    if existing:
        update_item(existing["id"], name or existing["name"], barcode or existing["barcode"],
                    category_id or existing["category_id"],
                    purchase_price if purchase_price is not None else existing["purchase_price"],
                    sale_price if sale_price is not None else existing["sale_price"],
                    quantity if quantity is not None else existing["quantity"],
                    min_quantity if min_quantity is not None else existing["min_quantity"])
        return existing["id"], "updated"
    else:
        new_id = add_item(name, barcode, category_id, purchase_price or 0, sale_price or 0,
                           quantity or 0, min_quantity if min_quantity is not None else 2)
        return new_id, "created"


# =====================================================================
# الموردون
# =====================================================================
def get_suppliers(search=""):
    if search:
        return query_all("SELECT * FROM suppliers WHERE name LIKE ? ORDER BY name", (f"%{search}%",))
    return query_all("SELECT * FROM suppliers ORDER BY name")


def get_or_create_supplier(name, phone="", notes=""):
    if not name:
        return None
    row = query_one("SELECT * FROM suppliers WHERE name=?", (name,))
    if row:
        return row["id"]
    return execute("INSERT INTO suppliers (name, phone, notes) VALUES (?,?,?)", (name, phone, notes))


def update_supplier(sid, name, phone, notes):
    execute("UPDATE suppliers SET name=?, phone=?, notes=? WHERE id=?", (name, phone, notes, sid))


def delete_supplier(sid):
    execute("DELETE FROM suppliers WHERE id=?", (sid,))


# =====================================================================
# الخزنة
# =====================================================================
def add_treasury_transaction(t_type, source, amount, ref_id=None, notes="", user=None):
    execute("""INSERT INTO treasury_transactions (date, type, source, ref_id, amount, notes, user_id, username)
               VALUES (?,?,?,?,?,?,?,?)""",
            (now_str(), t_type, source, ref_id, amount, notes,
             (user or {}).get("id"), (user or {}).get("username", "")))


def treasury_balance():
    inr = query_one("SELECT SUM(amount) as s FROM treasury_transactions WHERE type='in'")["s"] or 0
    outr = query_one("SELECT SUM(amount) as s FROM treasury_transactions WHERE type='out'")["s"] or 0
    return inr - outr


def get_treasury_transactions(date_from=None, date_to=None, search=""):
    q = "SELECT * FROM treasury_transactions WHERE 1=1"
    params = []
    if date_from:
        q += " AND date(date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(date) <= date(?)"
        params.append(date_to)
    if search:
        q += " AND (notes LIKE ? OR source LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY id DESC"
    return query_all(q, params)


# =====================================================================
# المبيعات
# =====================================================================
def generate_invoice_number(prefix="INV"):
    row = query_one("SELECT COUNT(*) as c FROM sales")
    n = (row["c"] or 0) + 1
    return f"{prefix}-{n:06d}"


def create_sale(invoice_number, customer_name, items, discount, notes="", user=None):
    """items: list of dict(item_id, item_name, quantity, price[, purchase_price])
       الربح = (سعر البيع - سعر الشراء) × الكمية لكل سطر"""
    subtotal = sum(i["quantity"] * i["price"] for i in items)
    total = max(subtotal - (discount or 0), 0)
    total_profit = 0
    for i in items:
        pp = i.get("purchase_price")
        if pp is None and i.get("item_id"):
            it = get_item(i["item_id"])
            pp = it["purchase_price"] if it else 0
        i["_purchase_price"] = pp or 0
        i["_profit"] = (i["price"] - i["_purchase_price"]) * i["quantity"]
        total_profit += i["_profit"]

    sale_id = execute("""INSERT INTO sales (invoice_number, date, customer_name, subtotal, discount, total, paid,
                          profit, notes, user_id, username) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                       (invoice_number, now_str(), customer_name, subtotal, discount or 0, total, total,
                        total_profit, notes, (user or {}).get("id"), (user or {}).get("username", "")))

    for i in items:
        line_total = i["quantity"] * i["price"]
        execute("""INSERT INTO sale_items (sale_id, item_id, item_name, quantity, price, purchase_price, total, profit)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (sale_id, i.get("item_id"), i["item_name"], i["quantity"], i["price"],
                 i["_purchase_price"], line_total, i["_profit"]))
        if i.get("item_id"):
            adjust_item_quantity(i["item_id"], -i["quantity"])

    add_treasury_transaction("in", "sale", total, ref_id=sale_id,
                              notes=f"فاتورة بيع {invoice_number}", user=user)
    return sale_id


def get_sales(date_from=None, date_to=None, search="", user_id=None):
    q = "SELECT * FROM sales WHERE 1=1"
    params = []
    if date_from:
        q += " AND date(date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(date) <= date(?)"
        params.append(date_to)
    if search:
        q += " AND (invoice_number LIKE ? OR customer_name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if user_id:
        q += " AND user_id = ?"
        params.append(user_id)
    q += " ORDER BY id DESC"
    return query_all(q, params)


def get_sale(sale_id):
    return query_one("SELECT * FROM sales WHERE id=?", (sale_id,))


def get_sale_items(sale_id):
    return query_all("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,))


def delete_sale(sale_id, user=None):
    for it in get_sale_items(sale_id):
        if it["item_id"]:
            adjust_item_quantity(it["item_id"], it["quantity"])
    sale = get_sale(sale_id)
    execute("DELETE FROM sales WHERE id=?", (sale_id,))
    if sale:
        add_treasury_transaction("out", "sale_void", sale["total"], ref_id=sale_id,
                                  notes=f"إلغاء فاتورة بيع {sale['invoice_number']}", user=user)


def total_sales_today():
    return query_one("SELECT SUM(total) as s FROM sales WHERE date(date)=date('now','localtime')")["s"] or 0


def total_profit_today():
    return query_one("SELECT SUM(profit) as s FROM sales WHERE date(date)=date('now','localtime')")["s"] or 0


def count_invoices_today():
    return query_one("SELECT COUNT(*) as c FROM sales WHERE date(date)=date('now','localtime')")["c"] or 0


def sales_series(days=7):
    return query_all("""SELECT date(date) as d, SUM(total) as total, SUM(profit) as profit FROM sales
                         WHERE date(date) >= date('now','localtime', ? )
                         GROUP BY date(date) ORDER BY d""", (f"-{days} day",))


def top_profit_items(date_from=None, date_to=None, limit=10):
    q = """SELECT sale_items.item_name as item_name, SUM(sale_items.quantity) as qty,
                  SUM(sale_items.total) as total_sales, SUM(sale_items.profit) as total_profit
           FROM sale_items JOIN sales ON sale_items.sale_id = sales.id WHERE 1=1"""
    params = []
    if date_from:
        q += " AND date(sales.date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(sales.date) <= date(?)"
        params.append(date_to)
    q += " GROUP BY sale_items.item_name ORDER BY total_profit DESC LIMIT ?"
    params.append(limit)
    return query_all(q, params)


# =====================================================================
# المشتريات
# =====================================================================
def create_purchase(invoice_number, supplier_id, items, notes="", user=None):
    total = sum(i["quantity"] * i["purchase_price"] for i in items)
    purchase_id = execute("""INSERT INTO purchases (invoice_number, date, supplier_id, total, notes, user_id, username)
                              VALUES (?,?,?,?,?,?,?)""",
                           (invoice_number, now_str(), supplier_id, total, notes,
                            (user or {}).get("id"), (user or {}).get("username", "")))
    for i in items:
        line_total = i["quantity"] * i["purchase_price"]
        execute("""INSERT INTO purchase_items (purchase_id, item_id, item_name, quantity, purchase_price, total)
                   VALUES (?,?,?,?,?,?)""",
                (purchase_id, i.get("item_id"), i["item_name"], i["quantity"], i["purchase_price"], line_total))
        if i.get("item_id"):
            adjust_item_quantity(i["item_id"], i["quantity"])
            execute("UPDATE items SET purchase_price=? WHERE id=?", (i["purchase_price"], i["item_id"]))
    add_treasury_transaction("out", "purchase", total, ref_id=purchase_id,
                              notes=f"فاتورة شراء {invoice_number}", user=user)
    return purchase_id


def get_purchases(date_from=None, date_to=None, search=""):
    q = """SELECT purchases.*, suppliers.name as supplier_name FROM purchases
           LEFT JOIN suppliers ON purchases.supplier_id = suppliers.id WHERE 1=1"""
    params = []
    if date_from:
        q += " AND date(purchases.date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(purchases.date) <= date(?)"
        params.append(date_to)
    if search:
        q += " AND (suppliers.name LIKE ? OR purchases.invoice_number LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY purchases.id DESC"
    return query_all(q, params)


def get_purchase_items(purchase_id):
    return query_all("SELECT * FROM purchase_items WHERE purchase_id=?", (purchase_id,))


def delete_purchase(purchase_id, user=None):
    purchase = query_one("SELECT * FROM purchases WHERE id=?", (purchase_id,))
    for it in get_purchase_items(purchase_id):
        if it["item_id"]:
            adjust_item_quantity(it["item_id"], -it["quantity"])
    execute("DELETE FROM purchases WHERE id=?", (purchase_id,))
    if purchase:
        add_treasury_transaction("in", "purchase_void", purchase["total"], ref_id=purchase_id,
                                  notes=f"إلغاء فاتورة شراء {purchase['invoice_number']}", user=user)


def total_purchases_today():
    return query_one("SELECT SUM(total) as s FROM purchases WHERE date(date)=date('now','localtime')")["s"] or 0


# =====================================================================
# المصاريف
# =====================================================================
def get_expense_types():
    return query_all("SELECT * FROM expense_types ORDER BY name")


def add_expense_type(name):
    execute("INSERT OR IGNORE INTO expense_types (name) VALUES (?)", (name,))


def get_or_create_expense_type(name):
    row = query_one("SELECT * FROM expense_types WHERE name=?", (name,))
    if row:
        return row["id"]
    return execute("INSERT INTO expense_types (name) VALUES (?)", (name,))


def add_expense(type_id, amount, notes="", user=None):
    eid = execute("INSERT INTO expenses (date, type_id, amount, notes, user_id, username) VALUES (?,?,?,?,?,?)",
                   (now_str(), type_id, amount, notes, (user or {}).get("id"), (user or {}).get("username", "")))
    add_treasury_transaction("out", "expense", amount, ref_id=eid, notes=notes, user=user)
    return eid


def get_expenses(date_from=None, date_to=None):
    q = """SELECT expenses.*, expense_types.name as type_name FROM expenses
           LEFT JOIN expense_types ON expenses.type_id = expense_types.id WHERE 1=1"""
    params = []
    if date_from:
        q += " AND date(expenses.date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(expenses.date) <= date(?)"
        params.append(date_to)
    q += " ORDER BY expenses.id DESC"
    return query_all(q, params)


def delete_expense(expense_id, user=None):
    exp = query_one("SELECT * FROM expenses WHERE id=?", (expense_id,))
    execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    if exp:
        add_treasury_transaction("in", "expense_void", exp["amount"], ref_id=expense_id,
                                  notes="إلغاء مصروف", user=user)


def total_expenses_today():
    return query_one("SELECT SUM(amount) as s FROM expenses WHERE date(date)=date('now','localtime')")["s"] or 0


# =====================================================================
# الجرد
# =====================================================================
def create_inventory_count(notes="", user=None):
    return execute("INSERT INTO inventory_counts (date, notes, user_id, username) VALUES (?,?,?,?)",
                    (now_str(), notes, (user or {}).get("id"), (user or {}).get("username", "")))


def add_inventory_count_item(count_id, item_id, item_name, system_qty, actual_qty):
    diff = actual_qty - system_qty
    execute("""INSERT INTO inventory_count_items (count_id, item_id, item_name, system_qty, actual_qty, diff)
               VALUES (?,?,?,?,?,?)""", (count_id, item_id, item_name, system_qty, actual_qty, diff))


def apply_inventory_count(count_id):
    for row in query_all("SELECT * FROM inventory_count_items WHERE count_id=?", (count_id,)):
        if row["item_id"]:
            set_item_quantity(row["item_id"], row["actual_qty"])


def get_inventory_counts():
    return query_all("SELECT * FROM inventory_counts ORDER BY id DESC")


def get_inventory_count_items(count_id):
    return query_all("SELECT * FROM inventory_count_items WHERE count_id=?", (count_id,))


# =====================================================================
# الأرباح والتقارير
# =====================================================================
def profit_between(d1, d2):
    sales_total = query_one("SELECT SUM(total) as s FROM sales WHERE date(date) BETWEEN date(?) AND date(?)",
                             (d1, d2))["s"] or 0
    gross_profit = query_one("SELECT SUM(profit) as s FROM sales WHERE date(date) BETWEEN date(?) AND date(?)",
                              (d1, d2))["s"] or 0
    expenses_total = query_one("SELECT SUM(amount) as s FROM expenses WHERE date(date) BETWEEN date(?) AND date(?)",
                                (d1, d2))["s"] or 0
    purchases_total = query_one("SELECT SUM(total) as s FROM purchases WHERE date(date) BETWEEN date(?) AND date(?)",
                                 (d1, d2))["s"] or 0
    net_profit = gross_profit - expenses_total
    return {
        "sales_total": sales_total,
        "gross_profit": gross_profit,
        "expenses_total": expenses_total,
        "purchases_total": purchases_total,
        "net_profit": net_profit,
    }


def net_profit_today():
    d = today_str()
    return profit_between(d, d)["net_profit"]


# =====================================================================
# نسخ احتياطي / استعادة (قاعدة بيانات خام)
# =====================================================================
def backup_db_to(dest_path):
    shutil.copy2(DB_PATH, dest_path)
    set_setting("last_backup", now_str())


def restore_db_from(src_path):
    shutil.copy2(src_path, DB_PATH)


ALL_TABLES = ["categories", "items", "suppliers", "sales", "sale_items", "purchases", "purchase_items",
              "expense_types", "expenses", "inventory_counts", "inventory_count_items",
              "treasury_transactions", "activity_log", "users"]
