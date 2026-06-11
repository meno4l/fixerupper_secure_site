import re

from app import create_app
from db import get_db
from seed import seed


def csrf(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "CSRF token missing"
    return match.group(1)


def run():
    seed()
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200

    token = csrf(response.get_data(as_text=True))
    response = client.post("/cart/add/1", data={"csrf_token": token}, follow_redirects=True)
    assert response.status_code == 200
    assert "added to your cart" in response.get_data(as_text=True)

    response = client.get("/cart")
    assert response.status_code == 200
    assert "Order Summary" in response.get_data(as_text=True)

    response = client.get("/checkout")
    assert response.status_code == 200
    assert "Sign in to confirm your order" in response.get_data(as_text=True)

    response = client.get("/login")
    token = csrf(response.get_data(as_text=True))
    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "jamie.customer@example.com",
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Confirm Order" in response.get_data(as_text=True)

    response = client.get("/logout")
    assert response.status_code == 405

    response = client.get("/register")
    token = csrf(response.get_data(as_text=True))
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "<script>alert(1)</script>",
            "email": "xss-test@example.com",
            "password": "Password123!",
        },
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Name must not contain HTML characters." in html
    assert "<script>alert(1)</script>" not in html

    response = client.get("/login")
    token = csrf(response.get_data(as_text=True))
    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "jamie.customer@example.com",
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Confirm Order" in response.get_data(as_text=True)

    token = csrf(response.get_data(as_text=True))
    response = client.post("/order/confirm", data={"csrf_token": token}, follow_redirects=True)
    assert response.status_code == 200
    assert "Order confirmed" in response.get_data(as_text=True)

    with app.app_context():
        stock = get_db().execute("SELECT stock FROM products WHERE id = ?", (1,)).fetchone()["stock"]
        assert stock == 17

    print("Smoke test passed")


if __name__ == "__main__":
    run()
