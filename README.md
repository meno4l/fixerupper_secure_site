# FixerUpper Secure E-Commerce Prototype

FixerUpper is a secure, coursework-friendly prototype e-commerce website for a hardware appliance retailer. It demonstrates a product catalogue, guest cart, secure login/registration, protected checkout, order confirmation, and a working SQLite database.

This project does **not** collect real payments and never stores card details.

## Features

- Responsive product catalogue with images, prices, and add-to-cart actions
- Shopping cart works before login
- Cart quantity update, remove item, totals, and checkout flow
- Checkout requires login or registration
- Secure customer registration and login
- Order confirmation page with persisted order and order items
- Product stock is reduced after a successful order
- Logout with full session cleanup
- SQLite database schema and seed products/sample users
- Friendly validation and flash messages

## Security Measures

- Passwords are hashed with `bcrypt`; plain-text passwords are never stored.
- SQL injection protection is handled through SQLite parameterized queries.
- Sessions are configured with `HttpOnly`, `SameSite=Lax`, expiry, and optional `Secure` cookies.
- Session identifiers are rotated after login/registration by clearing the old session before setting authenticated values.
- Logout clears and destroys user session state.
- CSRF tokens protect all state-changing POST forms.
- Security headers add a content security policy, clickjacking protection, content-type sniffing protection, and referrer controls.
- Jinja auto-escaping is used for template output.
- User input is trimmed, validated, and never rendered with unsafe HTML.
- Checkout and order confirmation routes require authentication.

## Setup

1. Install Python 3.11+.

2. Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create and seed the SQLite database:

```powershell
python seed.py
```

5. Start the development server:

```powershell
python app.py
```

To enable Flask debug mode while developing:

```powershell
$env:FLASK_DEBUG='1'
python app.py
```

6. Open:

```text
http://127.0.0.1:5000
```

## Sample Logins

```text
Email: jamie.customer@example.com
Password: Password123!

Email: priya.customer@example.com
Password: Password123!
```

## Project Structure

```text
fixerupper_secure_site/
  app.py
  db.py
  seed.py
  schema.sql
  requirements.txt
  README.md
  static/
    css/styles.css
    js/main.js
    images/*.svg
  templates/
    base.html
    catalogue.html
    cart.html
    checkout_gate.html
    confirm_order.html
    login.html
    register.html
    order_success.html
  instance/
    fixerupper.sqlite
```

The `instance/` database file is created when you run `python seed.py`.

## Smoke Test

Run the basic end-to-end check with:

```powershell
python smoke_test.py
```

The smoke test reseeds the SQLite database, adds a product to the cart, logs in, confirms an order, and checks that product stock is reduced.

## Image Credits

Product photos are loaded from Wikimedia Commons using `Special:Redirect/file` URLs:

- `CordlessDrill.jpg` by Greg Hume, CC BY-SA 3.0
- `Sander, Vlakschuurmachine.jpg` by Rasbak, CC BY-SA
- `Drum of a washing machine (Bosch Maxx WFO 2440).jpg` by Smial, CC BY-SA
- `Electrical stove Mora EUROLINE 3430 (1).jpg` by Pavel Sevela, CC BY-SA
- `DeWalt circular saw (51634542954).jpg` by Puddin Tain, CC BY-SA 2.0
- `Ice Maker (5881247006).jpg`, NIST/Flickr source via Wikimedia Commons

## Marking Notes

- The database tables are `users`, `products`, `orders`, and `order_items`.
- Cart contents are stored in the signed server-side session until checkout.
- Orders are persisted only after the authenticated customer confirms the order, and stock is updated in the same checkout flow.
- Payment collection is intentionally represented by a no-payment notice on the confirm order page.
