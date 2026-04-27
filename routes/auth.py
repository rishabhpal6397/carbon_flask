"""
CarbonIQ – Authentication Blueprint
Handles /login, /register, /logout.

KEY FIX: mongo is obtained via get_mongo() *inside* each view function
so it always runs within a live request context after init_app() fires.
Never import the bare PyMongo() shell at module level from blueprints.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import mongo
from models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
          # resolved inside request context ✓
        username = request.form.get("username", "").strip()
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")
        if User.get_by_email(email):
            flash("An account with this email already exists.", "error")
            return render_template("register.html")
        if User.get_by_username(username):
            flash("This username is already taken.", "error")
            return render_template("register.html")

        user = User.create(username, email, password)
        login_user(user)
        flash(f"Welcome, {user.username}! Your account has been created.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
          # resolved inside request context ✓
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")

        user_doc = User.get_by_email(email)
        if not user_doc or not User.check_password(password, user_doc["password"]):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        user = User(user_doc)
        login_user(user, remember=True)
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))