from pathlib import Path

import bcrypt

from app import create_app
from db import get_db, init_db
from sample_data import PRODUCTS, USERS


def seed():
    app = create_app()
    db_path = Path(app.config["DATABASE"])
    if db_path.exists():
        db_path.unlink()
    init_db(app)
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM order_items")
        db.execute("DELETE FROM orders")
        db.execute("DELETE FROM products")
        db.execute("DELETE FROM users")

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
    print("Database seeded at instance/fixerupper.sqlite")


if __name__ == "__main__":
    seed()
