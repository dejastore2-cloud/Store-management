# -*- coding: utf-8 -*-
"""
إدارة تسجيل الدخول والصلاحيات (مدير / موظف)
"""
from functools import wraps
from flask import session, redirect, url_for, request, flash, abort

import db


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    user = db.get_user_by_id(uid)
    if not user or not user["active"]:
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login", next=request.path))
        if user["role"] != "admin":
            flash("هذه الصفحة مخصصة لمدير النظام فقط", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def can_delete(user):
    return user and user["role"] == "admin"


def can_manage_settings(user):
    return user and user["role"] == "admin"
