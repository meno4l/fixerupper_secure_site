import os
import re
import secrets
import sqlite3
from datetime import timedelta
from functools import wraps
from pathlib import Path

import bcrypt
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from db import get_db, init_app, init_db
from sample_data import PRODUCTS, USERS


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_QUANTITY = 20


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    database_path = os.environ.get("DATABASE")
    if database_path is None:
        database_path = "/tmp/fixerupper.sqlite" if os.environ.get("VERCEL") else os.path.join(app.instance_path, "fixerupper.sqlite")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-this-secret-key"),
        DATABASE=database_path,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_COOKIE_SECURE") == "1",
    )
    os.makedirs(app.instance_path, exist_ok=True)
    init_app(app)
    ensure_seeded_database(app)

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' https://commons.wikimedia.org https://upload.wikimedia.org data:; "
            "style-src 'self'; "
            "script-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.before_request
    def refresh_session_security():
        session.permanent = True
        if request.method == "POST":
            form_token = request.form.get("csrf_token", "")
            session_token = session.get("csrf_token", "")
            if not form_token or not secrets.compare_digest(form_token, session_token):
                flash("Security check failed. Please try again.", "error")
                return redirect(request.referrer or url_for("catalogue"))

    @app.context_processor
    def inject_globals():
        # Per-session CSRF token protects state-changing cart, auth, and order forms.
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        return {
            "cart_count": sum(session.get("cart", {}).values()),
            "current_user": session.get("user"),
            "csrf_token": session["csrf_token"],
        }

    @app.template_filter("currency")
    def currency(cents):
        return f"GBP {cents / 100:,.2f}"

    def login_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if not session.get("user"):
                flash("Please log in or create an account to continue checkout.", "info")
                return redirect(url_for("login", next=request.full_path))
            return view(**kwargs)

        return wrapped_view

    def get_cart_items():
        cart = session.get("cart", {})
        if not cart:
            return [], 0

        product_ids = []
        for product_id in cart.keys():
            try:
                product_ids.append(int(product_id))
            except (TypeError, ValueError):
                continue

        if not product_ids:
            return [], 0

        placeholders = ",".join("?" for _ in product_ids)
        products = get_db().execute(
            f"SELECT id, name, description, price_cents, image_filename, image_url, stock FROM products WHERE id IN ({placeholders})",
            product_ids,
        ).fetchall()

        items = []
        total_cents = 0
        for product in products:
            try:
                requested_quantity = int(cart.get(str(product["id"]), 0))
            except (TypeError, ValueError):
                requested_quantity = 0
            quantity = min(requested_quantity, product["stock"], MAX_QUANTITY)
            if quantity <= 0:
                continue
            line_total = product["price_cents"] * quantity
            total_cents += line_total
            items.append({"product": product, "quantity": quantity, "line_total": line_total})
        return items, total_cents

    def normalize_cart():
        items, _total = get_cart_items()
        session["cart"] = {str(item["product"]["id"]): item["quantity"] for item in items}
        session.modified = True

    @app.route("/")
    def catalogue():
        products = get_db().execute(
            "SELECT id, name, description, price_cents, image_filename, image_url, stock FROM products ORDER BY id"
        ).fetchall()
        return render_template("catalogue.html", products=products)

    @app.post("/cart/add/<int:product_id>")
    def add_to_cart(product_id):
        product = get_db().execute(
            "SELECT id, name, stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if product is None:
            flash("That product could not be found.", "error")
            return redirect(url_for("catalogue"))

        cart = session.get("cart", {})
        current_qty = int(cart.get(str(product_id), 0))
        if current_qty >= min(product["stock"], MAX_QUANTITY):
            flash(f"{product['name']} is already at the maximum cart quantity.", "warning")
        else:
            cart[str(product_id)] = current_qty + 1
            session["cart"] = cart
            flash(f"{product['name']} added to your cart.", "success")
        return redirect(request.referrer or url_for("catalogue"))

    @app.route("/cart")
    def cart():
        normalize_cart()
        items, total_cents = get_cart_items()
        return render_template("cart.html", items=items, total_cents=total_cents)

    @app.post("/cart/update/<int:product_id>")
    def update_cart(product_id):
        quantity = request.form.get("quantity", "1")
        try:
            quantity_int = int(quantity)
        except ValueError:
            flash("Please enter a valid quantity.", "error")
            return redirect(url_for("cart"))

        product = get_db().execute(
            "SELECT id, name, stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if product is None:
            flash("That product could not be found.", "error")
            return redirect(url_for("cart"))

        cart = session.get("cart", {})
        if quantity_int <= 0:
            cart.pop(str(product_id), None)
            flash(f"{product['name']} removed from your cart.", "info")
        else:
            safe_qty = min(quantity_int, product["stock"], MAX_QUANTITY)
            cart[str(product_id)] = safe_qty
            flash(f"{product['name']} quantity updated.", "success")
        session["cart"] = cart
        return redirect(url_for("cart"))

    @app.post("/cart/remove/<int:product_id>")
    def remove_from_cart(product_id):
        cart = session.get("cart", {})
        cart.pop(str(product_id), None)
        session["cart"] = cart
        flash("Item removed from your cart.", "info")
        return redirect(url_for("cart"))

    @app.route("/checkout")
    def checkout():
        normalize_cart()
        if not session.get("cart"):
            flash("Your cart is empty. Add a product before checkout.", "info")
            return redirect(url_for("catalogue"))
        if not session.get("user"):
            return render_template("checkout_gate.html")
        return redirect(url_for("confirm_order"))

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            error = validate_registration(name, email, password)
            if error:
                flash(error, "error")
                return render_template("register.html", name=name, email=email)

            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            try:
                db = get_db()
                cursor = db.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, password_hash),
                )
                db.commit()
            except sqlite3.IntegrityError:
                flash("An account already exists for that email address.", "error")
                return render_template("register.html", name=name, email=email)

            # Clearing rotates the session contents before authentication state is set.
            cart_before_auth = session.get("cart", {})
            session.clear()
            session["csrf_token"] = secrets.token_urlsafe(32)
            session["cart"] = cart_before_auth
            session["user"] = {"id": cursor.lastrowid, "name": name, "email": email}
            flash("Welcome to FixerUpper. Your account is ready.", "success")
            return redirect(url_for("confirm_order") if session.get("cart") else url_for("catalogue"))

        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()

            if user is None or not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                flash("Email or password is incorrect.", "error")
                return render_template("login.html", email=email)

            cart_before_auth = session.get("cart", {})
            session.clear()
            session["csrf_token"] = secrets.token_urlsafe(32)
            session["cart"] = cart_before_auth
            session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"]}
            flash(f"Good to see you, {user['name']}.", "success")
            return redirect(url_for("confirm_order") if session.get("cart") else url_for("catalogue"))

        return render_template("login.html")

    @app.route("/logout", methods=("POST",))
    def logout():
        session.clear()
        flash("You have been logged out successfully.", "success")
        return redirect(url_for("catalogue"))

    @app.route("/order/confirm")
    @login_required
    def confirm_order():
        normalize_cart()
        items, total_cents = get_cart_items()
        if not items:
            flash("Your cart is empty. Add a product before checkout.", "info")
            return redirect(url_for("catalogue"))
        return render_template("confirm_order.html", items=items, total_cents=total_cents)

    @app.post("/order/confirm")
    @login_required
    def place_order():
        normalize_cart()
        items, total_cents = get_cart_items()
        if not items:
            flash("Your cart is empty. Add a product before checkout.", "info")
            return redirect(url_for("catalogue"))

        db = get_db()
        try:
            cursor = db.execute(
                "INSERT INTO orders (user_id, total_cents, status) VALUES (?, ?, ?)",
                (session["user"]["id"], total_cents, "confirmed"),
            )
            order_id = cursor.lastrowid
            for item in items:
                product = item["product"]
                stock_update = db.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (item["quantity"], product["id"], item["quantity"]),
                )
                if stock_update.rowcount != 1:
                    db.rollback()
                    normalize_cart()
                    flash("Some items no longer have enough stock. Please review your cart.", "warning")
                    return redirect(url_for("confirm_order"))

                db.execute(
                    """
                    INSERT INTO order_items
                        (order_id, product_id, product_name, unit_price_cents, quantity)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, product["id"], product["name"], product["price_cents"], item["quantity"]),
                )
            db.commit()
        except sqlite3.Error:
            db.rollback()
            flash("We could not confirm your order. Please try again.", "error")
            return redirect(url_for("confirm_order"))

        session["cart"] = {}
        flash("Order confirmed. No payment details were collected for this prototype.", "success")
        return redirect(url_for("order_success", order_id=order_id))

    @app.route("/order/success/<int:order_id>")
    @login_required
    def order_success(order_id):
        order = get_db().execute(
            "SELECT id, total_cents, created_at FROM orders WHERE id = ? AND user_id = ?",
            (order_id, session["user"]["id"]),
        ).fetchone()
        if order is None:
            flash("That order could not be found.", "error")
            return redirect(url_for("catalogue"))
        items = get_db().execute(
            "SELECT product_name, unit_price_cents, quantity FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,),
        ).fetchall()
        return render_template("order_success.html", order=order, items=items)

    return app


def ensure_seeded_database(app):
    db_path = Path(app.config["DATABASE"])
    if not db_path.exists():
        init_db(app)

    with app.app_context():
        db = get_db()
        try:
            product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        except sqlite3.OperationalError:
            init_db(app)
            product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]

        if product_count:
            return

        db.executemany(
            """
            INSERT INTO products (name, description, price_cents, image_filename, image_url, stock)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            PRODUCTS,
        )
        for name, email, password in USERS:
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
        db.commit()


def validate_registration(name, email, password):
    if not name or len(name) > 80:
        return "Please enter your name using 1 to 80 characters."
    if not EMAIL_RE.match(email) or len(email) > 120:
        return "Please enter a valid email address."
    if len(password) < 10:
        return "Password must be at least 10 characters."
    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        return "Password must include uppercase and lowercase letters."
    if not re.search(r"\d", password):
        return "Password must include at least one number."
    return None


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
