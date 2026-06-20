# -*- coding: utf-8 -*-
"""
تطبيق نظام الكاشير وإدارة المخزون - نسخة الويب
Flask + SQLite | يدعم PWA وعمل من المتصفح على الموبايل والكمبيوتر
"""
import os
import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file, send_from_directory)

import db
from auth import login_required, admin_required, current_user
from routes.items import items_bp
from routes.sales import sales_bp
from routes.other import (purchases_bp, expenses_bp, reports_bp,
                           inventory_bp, treasury_bp, settings_bp)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "gift-shop-secret-2025-xK9!mZ")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB

# تهيئة قاعدة البيانات
db.init_db()

# تسجيل الـ Blueprints
app.register_blueprint(items_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(purchases_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(treasury_bp)
app.register_blueprint(settings_bp)


# ------------------------------------------------------------------
# Context processor: متغيرات مشتركة لكل القوالب
# ------------------------------------------------------------------
@app.context_processor
def inject_globals():
    user = current_user()
    s = db.get_all_settings()
    return {
        "user": user,
        "shop_name": s.get("shop_name", "محل الهدايا"),
        "shop_logo": s.get("shop_logo", ""),
        "primary_color": s.get("primary_color", "#6C5CE7"),
        "accent_color": s.get("accent_color", "#00CEC9"),
        "currency": s.get("currency", "ج.م"),
        "theme_mode": s.get("theme_mode", "light"),
    }


# ------------------------------------------------------------------
# صفحة تسجيل الدخول
# ------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    s = db.get_all_settings()
    tpl = s.get("login_template", "classic")
    error = None
    username = ""
    next_url = request.args.get("next", "")

    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next", "")
        user = db.check_login(username, password)
        if user:
            session["user_id"] = user["id"]
            db.log_activity(user, "تسجيل دخول", f"من {request.remote_addr}")
            return redirect(next_url or url_for("dashboard"))
        error = "اسم المستخدم أو كلمة المرور غير صحيحة"

    return render_template("login.html", settings=s, tpl=tpl, error=error,
                            username=username, next_url=next_url)


@app.route("/logout")
def logout():
    user = current_user()
    if user:
        db.log_activity(user, "تسجيل خروج", "")
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------------
# لوحة التحكم (Dashboard)
# ------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    user = current_user()
    period = request.args.get("period", "today")
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")
    today = datetime.date.today()

    if period == "today":
        date_from = date_to = today.strftime("%Y-%m-%d")
    elif period == "week":
        date_from = (today - datetime.timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")
    elif period == "month":
        date_from = today.strftime("%Y-%m-01")
        date_to = today.strftime("%Y-%m-%d")
    elif period == "custom" and date_from and date_to:
        pass
    else:
        date_from = date_to = today.strftime("%Y-%m-%d")

    summary = db.profit_between(date_from, date_to)
    kpi = {
        "sales": summary["sales_total"],
        "purchases": summary["purchases_total"],
        "expenses": summary["expenses_total"],
        "profit": summary["net_profit"],
        "gross_profit": summary["gross_profit"],
        "invoices": len(db.get_sales(date_from=date_from, date_to=date_to)),
        "items_count": db.count_items(),
        "treasury": db.treasury_balance(),
    }
    top_items = db.top_profit_items(date_from=date_from, date_to=date_to, limit=7)
    series = db.sales_series(days=7)
    chart_labels = [r["d"] for r in series]
    chart_sales = [r["total"] or 0 for r in series]
    chart_profit = [r["profit"] or 0 for r in series]

    return render_template("dashboard.html", user=user,
                            active_page="dashboard", page_title="لوحة التحكم",
                            kpi=kpi, top_items=top_items, period=period,
                            date_from=date_from, date_to=date_to,
                            chart_labels=chart_labels,
                            chart_sales=chart_sales,
                            chart_profit=chart_profit)


# ------------------------------------------------------------------
# ملفات PWA (manifest.json + service worker)
# ------------------------------------------------------------------
@app.route("/static/manifest.json")
def manifest():
    s = db.get_all_settings()
    primary = s.get("primary_color", "#6C5CE7")
    shop_name = s.get("shop_name", "نظام الكاشير")
    manifest_data = {
        "name": shop_name,
        "short_name": shop_name[:15],
        "description": "نظام الكاشير وإدارة المخزون",
        "start_url": "/",
        "display": "standalone",
        "background_color": primary,
        "theme_color": primary,
        "lang": "ar",
        "dir": "rtl",
        "icons": [
            {"src": "/static/icons/app-icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/app-icon-512.png", "sizes": "512x512", "type": "image/png"},
        ]
    }
    return jsonify(manifest_data)


@app.route("/static/sw.js")
def service_worker():
    sw_content = r"""
const CACHE = 'gifshop-v1';
const STATIC = [
  '/', '/login',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/data-table.js',
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC).catch(()=>{})));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(r => {
      if(r && r.status===200) {
        const clone = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return r;
    }).catch(() => caches.match(e.request))
  );
});
"""
    return app.response_class(sw_content, mimetype="application/javascript")


# ------------------------------------------------------------------
# قالب معاينة المبيعات للاستيراد (لا يوجد ملف بعد — أنشئه هنا)
# ------------------------------------------------------------------
@app.route("/sales/import/preview")
@admin_required
def sales_import_preview():
    return redirect(url_for("sales.list_sales") + "?tab=list")


# ------------------------------------------------------------------
# صفحة الخطأ
# ------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="الصفحة غير موجودة"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="غير مسموح بالوصول"), 403


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="خطأ داخلي في الخادم"), 500


# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
