import os
import re

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from webapp import db
from webapp.models import User

auth = Blueprint("auth", __name__)
EMAIL_VERIFIER = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")


def password_check(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        4 characters length or more
    """
    # Calculating the length
    length_error = len(password) < 4
    # Overall result
    password_ok = not (length_error)
    return password_ok


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        pwd = request.form.get("password")

        lookup = User.query.filter_by(email=email).first()
        if lookup:
            if check_password_hash(lookup.password, pwd):
                flash("Login successful!", category="success")
                login_user(lookup, remember=True)
                return redirect(url_for("views.home"))
        flash("Invalid credentials.", category="error")

    return render_template("login.html", user=current_user)


@auth.route("/logout")
@login_required
def logout():
    flash("Logout successful.", category="success")
    logout_user()
    return redirect(url_for("auth.login"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        full_name = request.form.get("fullName")
        pwd1 = request.form.get("password1")
        pwd2 = request.form.get("password2")

        lookup = User.query.filter_by(email=email).first()
        if lookup:
            flash("Email already in use.", category="error")
        elif not EMAIL_VERIFIER.match(email):
            flash("Invalid email.", category="error")
        elif len(full_name) < 2:
            flash("Please enter your real full name.", category="error")
        elif pwd1 != pwd2:
            flash("Passwords do not match.", category="error")
        # Uncomment for production
        # elif not password_check(pwd1):
        #     flash("Invalid password format.", category='error')
        else:
            is_admin = 1 if email == "admin@a.a" else 0
            new_user = User(full_name=full_name, email=email, password=generate_password_hash(pwd1, method="sha256"),
                            is_trained=0, is_admin=is_admin)
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user, remember=True)

            flash("Account created!", category="success")
            return redirect(url_for("views.home"))

    return render_template("register.html", user=current_user)
