import pytest
from app import create_app
from models import Customer, Invoice, InvoiceItem, Lead, Payment, Product, User, calculate_item, db


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test"})
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="admin@example.com", password="Admin@123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def test_startup_and_auth(client):
    response = login(client)
    assert response.status_code == 200
    assert b"Pipeline snapshot" in response.data
    assert client.get("/logout").status_code == 302


def test_lead_creation_and_api(client, app):
    login(client)
    response = client.post("/leads", data={"name": "Test Lead", "email": "test@example.com", "estimated_value": "1200"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert Lead.query.filter_by(name="Test Lead").first()
    api = client.get("/api/leads")
    assert api.status_code == 200 and b"Test Lead" in api.data


def test_calculation_and_payment_balance(client, app):
    login(client)
    with app.app_context():
        c = Customer(customer_number="CUST-X", name="Test Customer")
        db.session.add(c)
        p = Product(product_number="PROD-X", name="Test", selling_price=100, tax_percentage=18)
        db.session.add(p); db.session.flush()
        inv = Invoice(invoice_number="INV-X", customer_id=c.id, total=118)
        db.session.add(inv); db.session.commit()
        from decimal import Decimal
        assert calculate_item(2, 100, 10, 18)[3] == Decimal("212.4")
        iid = inv.id
    ok = client.post(f"/invoices/{iid}/payments", data={"amount": "50"}, follow_redirects=True)
    assert b"Payment recorded" in ok.data
    bad = client.post(f"/invoices/{iid}/payments", data={"amount": "1000"}, follow_redirects=True)
    assert b"must be positive" in bad.data


def test_role_protection(client):
    response = client.post("/login", data={"email": "sales@example.com", "password": "Sales@123"}, follow_redirects=False)
    assert response.status_code == 302
    assert client.get("/settings").status_code == 403
