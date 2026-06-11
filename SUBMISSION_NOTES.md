# Submission Notes

## Project

FixerUpper Secure E-Commerce Prototype

Live deployment: https://fixerupper-secure-site.vercel.app/

GitHub repository: https://github.com/meno4l/fixerupper_secure_site

## Sample Customer Accounts

```text
Email: jamie.customer@example.com
Password: Password123!

Email: priya.customer@example.com
Password: Password123!
```

## Practical Requirement Coverage

- Products are displayed on the catalogue page with names, descriptions, prices, stock counts, and images.
- Customers can add products to the shopping cart without logging in.
- The cart allows quantity updates, item removal, and checkout.
- Checkout prompts the customer to log in or register.
- Registration and login both preserve the guest cart and continue to order confirmation.
- Confirmed orders are stored in the SQLite database with order items.
- Product stock is reduced after a successful order.
- The customer can log out successfully.
- No payment details are collected or stored.

## Security Measures

- Password theft: customer passwords are hashed with bcrypt before storage.
- SQL injection: database access uses parameterized SQLite queries.
- Session hijacking: sessions use HttpOnly cookies, SameSite=Lax, a 30-minute lifetime, and session clearing on login, registration, and logout.
- CSRF: all state-changing POST forms include CSRF tokens that are checked before the route runs.
- XSS: Jinja auto-escaping is used, user-controlled output is not rendered as raw HTML, and a content security policy is sent.
- Clickjacking and browser hardening: responses include X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Content-Security-Policy headers.

## Testing

Run the local smoke test with:

```powershell
python smoke_test.py
```

The smoke test reseeds the database, adds a product to the cart, logs in, confirms an order, and checks that stock is reduced.

## Deployment Note

The Vercel deployment uses SQLite in temporary serverless storage for prototype demonstration. This is suitable for showing the required workflow, but a real production deployment should use a hosted persistent database.
