
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, redirect, render_template, request, url_for, abort

DB_PATH = Path(__file__).with_name("membership.db")

app = Flask(__name__)


# ---------- 資料庫工具 ---------- #
def init_db() -> None:
    """首次執行時建立資料表並插入預設帳號。"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                iid       INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT NOT NULL UNIQUE,
                email     TEXT NOT NULL UNIQUE,
                password  TEXT NOT NULL,
                phone     TEXT,
                birthdate TEXT
            );
            """
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO members
            (username, email, password, phone, birthdate)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("admin", "admin@example.com", "admin123", "0912345678", "1990-01-01"),
        )
        conn.commit()


def query_db(query: str, params: tuple[Any, ...] = (), one: bool = False):
    """通用查詢（只讀）。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv


def exec_db(query: str, params: tuple[Any, ...] = ()) -> None:
    """通用寫入 / 更新 / 刪除。"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(query, params)
        conn.commit()


# ---------- 自訂 Jinja 過濾器 ---------- #
@app.template_filter("add_stars")
def add_stars(s: str) -> str:
    """為用戶名前後加星號。"""
    return f"★{s}★"


# ---------- 路由 ---------- #
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()
    phone = request.form.get("phone", "").strip()
    birthdate = request.form.get("birthdate", "").strip()

    if not (username and email and password):
        return render_template("error.html", msg="請輸入用戶名、電子郵件和密碼")

    if query_db("SELECT 1 FROM members WHERE username = ?", (username,), one=True):
        return render_template("error.html", msg="用戶名已存在")

    exec_db(
        """INSERT INTO members (username, email, password, phone, birthdate)
        VALUES (?, ?, ?, ?, ?);""",
        (username, email, password, phone, birthdate),
    )
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not (email and password):
        return render_template("error.html", msg="請輸入電子郵件和密碼")

    user = query_db(
        "SELECT iid, username FROM members WHERE email = ? AND password = ?",
        (email, password),
        one=True,
    )
    if user:
        return redirect(url_for("welcome", iid=user["iid"]))
    return render_template("error.html", msg="電子郵件或密碼錯誤")


@app.route("/welcome/<int:iid>")
def welcome(iid: int):
    user = query_db("SELECT * FROM members WHERE iid = ?", (iid,), one=True)
    if not user:
        abort(404)
    return render_template("welcome.html", user=user)


@app.route("/edit_profile/<int:iid>", methods=["GET", "POST"])
def edit_profile(iid: int):
    user = query_db("SELECT * FROM members WHERE iid = ?", (iid,), one=True)
    if not user:
        abort(404)

    if request.method == "GET":
        return render_template("edit_profile.html", user=user)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()
    phone = request.form.get("phone", "").strip()
    birthdate = request.form.get("birthdate", "").strip()

    if not (email and password):
        return render_template("error.html", msg="請輸入電子郵件和密碼")

    taken = query_db(
        "SELECT 1 FROM members WHERE email = ? AND iid != ?", (email, iid), one=True
    )
    if taken:
        return render_template("error.html", msg="電子郵件已被使用")

    exec_db(
        """UPDATE members SET email = ?, password = ?, phone = ?, birthdate = ?
        WHERE iid = ?;""",
        (email, password, phone, birthdate, iid),
    )
    return redirect(url_for("welcome", iid=iid))


@app.route("/delete/<int:iid>")
def delete_user(iid: int):
    exec_db("DELETE FROM members WHERE iid = ?", (iid,))
    return redirect(url_for("index"))


# ---------- 主程式入口 ---------- #
init_db()
