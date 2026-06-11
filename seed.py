from pathlib import Path

import bcrypt

from app import create_app
from db import get_db, init_db


PRODUCTS = [
    (
        "DeWalt 18V Combi Drill",
        "Cordless drill driver with two-speed gearbox, LED work light, and carry case.",
        8999,
        "drill.svg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/CordlessDrill.jpg?width=900",
        18,
    ),
    (
        "Bosch Multi-Sander",
        "Compact detail sander for doors, shelving, and renovation finishing work.",
        5499,
        "sander.svg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Sander,_Vlakschuurmachine.jpg?width=900",
        22,
    ),
    (
        "Samsung EcoWash 8kg Washer",
        "Efficient freestanding washing machine with quick wash and quiet spin modes.",
        36900,
        "washer.svg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Drum_of_a_washing_machine_(Bosch_Maxx_WFO_2440).jpg?width=900",
        8,
    ),
    (
        "Hotpoint 60cm Electric Cooker",
        "Fan oven, ceramic hob, and easy-clean enamel lining for everyday meals.",
        42900,
        "cooker.svg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Electrical_stove_Mora_EUROLINE_3430_(1).jpg?width=900",
        6,
    ),
    (
        "Makita Circular Saw",
        "Lightweight 165mm circular saw with dust extraction port and safety guard.",
        11900,
        "saw.svg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/DeWalt_circular_saw_(51634542954).jpg?width=900",
        14,
    ),
    (
        "FridgeMaster Tall Fridge",
        "A+ rated tall larder fridge with adjustable shelves and crisp produce drawer.",
        29900,
        "fridge.svg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ice_Maker_(5881247006).jpg?width=900",
        5,
    ),
]

USERS = [
    ("Jamie Carter", "jamie.customer@example.com", "Password123!"),
    ("Priya Shah", "priya.customer@example.com", "Password123!"),
]


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
