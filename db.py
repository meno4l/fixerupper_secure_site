import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    db_path = Path(app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db = get_db()
        schema = Path(app.root_path, "schema.sql").read_text(encoding="utf-8")
        db.executescript(schema)
        db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
