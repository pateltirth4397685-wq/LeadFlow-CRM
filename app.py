import csv
import io
import os
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Flask, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph
from werkzeug.exceptions import HTTPException

from config import Config, TestingConfig
from models import (
    BusinessSetting, Customer, FollowUp, Invoice, InvoiceItem, Lead, Notification, OTP,
    Payment, Product, Quotation, QuotationItem, Task, User, calculate_item, db,
)

login_manager = LoginManager()
login_manager.login_view = "login"


def create_app(test_config=None):
    app = Flask(__name__)
    if isinstance(test_config, dict):
        app.config.from_object(Config)
        app.config.update(test_config)
    else:
        app.config.from_object(test_config or Config)
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        seed_demo()

    register_routes(app)
    return app


def seed_demo():
    if User.query.first():
        if not BusinessSetting.query.first():
            db.session.add(BusinessSetting())
            db.session.commit()
        return
    admin = User(name="Demo Admin", email="admin@example.com", phone="9999999999", role="admin")
    admin.set_password("Admin@123")
    sales = User(name="Demo Sales", email="sales@example.com", phone="9999999998", role="sales")
    sales.set_password("Sales@123")
    db.session.add_all([admin, sales, BusinessSetting()])
    db.session.flush()
    for i in range(1, 11):
        db.session.add(Lead(
            lead_number=next_number("LEAD", Lead), name=f"Prospect {i}", company=f"Acme Partner {i}",
            email=f"prospect{i}@example.com", phone=f"90000000{i:02d}", source=["Website", "Referral", "WhatsApp"][i % 3],
            status=["New", "Contacted", "Qualified", "Proposal", "Won"][i % 5],
            priority=["Low", "Medium", "High"][i % 3], estimated_value=Decimal(10000 + i * 2500),
            assigned_to=sales.id,
        ))
    for i in range(1, 6):
        db.session.add(Customer(customer_number=next_number("CUST", Customer), name=f"Customer {i}",
                                company=f"Customer Co {i}", email=f"customer{i}@example.com",
                                phone=f"88888888{i:02d}", state="Maharashtra"))
    for i in range(1, 11):
        db.session.add(Product(product_number=next_number("PROD", Product), name=f"Service/Product {i}",
                               sku=f"SKU-{i:03d}", unit="PCS", selling_price=Decimal(1000 + i * 100),
                               tax_percentage=18, stock_quantity=100))
    db.session.commit()


def next_number(prefix, model):
    year = datetime.utcnow().year
    return f"{prefix}-{year}-{model.query.count() + 1:04d}"


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def val(name, default=""):
    return request.form.get(name, default).strip()


def dec(value, default="0"):
    try:
        return Decimal(str(value or default))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def parse_date(value, fallback=None):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else fallback
    except ValueError:
        return fallback


def calculate_document(doc, item_cls):
    subtotal = discount = tax = total = Decimal("0")
    for item in doc.items:
        gross, disc, tax_amount, amount = calculate_item(item.quantity, item.rate, item.discount, item.tax)
        item.amount = amount
        subtotal += gross
        discount += disc
        tax += tax_amount
        total += amount
    doc.subtotal, doc.discount_total, doc.tax_total, doc.total = subtotal, discount, tax, total


def document_items(payload, item_cls, document_id=None):
    raw = payload.get("items", [])
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = []
    for data in raw:
        quantity, rate = dec(data.get("quantity", 1)), dec(data.get("rate", 0))
        product = db.session.get(Product, data.get("product_id")) if data.get("product_id") else None
        item_data = dict(product_id=product.id if product else None, description=data.get("description") or (product.name if product else ""),
                         quantity=quantity, unit=data.get("unit") or (product.unit if product else "PCS"),
                         rate=rate if rate else (product.selling_price if product else 0),
                         discount=dec(data.get("discount")), tax=dec(data.get("tax") or (product.tax_percentage if product else 0)))
        if document_id:
            item_data["quotation_id" if item_cls is QuotationItem else "invoice_id"] = document_id
        item = item_cls(**item_data)
        db.session.add(item)
        yield item


def serialize(obj):
    if isinstance(obj, (Lead, Customer, Product)):
        fields = {
            Lead: ["id", "lead_number", "name", "company", "email", "phone", "source", "status", "priority", "estimated_value"],
            Customer: ["id", "customer_number", "name", "company", "email", "phone", "city", "state"],
            Product: ["id", "product_number", "name", "sku", "unit", "selling_price", "tax_percentage", "stock_quantity", "active"],
        }[type(obj)]
    elif isinstance(obj, Quotation):
        fields = ["id", "quotation_number", "customer_id", "status", "subtotal", "discount_total", "tax_total", "total"]
    elif isinstance(obj, Invoice):
        fields = ["id", "invoice_number", "customer_id", "status", "subtotal", "discount_total", "tax_total", "total"]
    elif isinstance(obj, Payment):
        fields = ["id", "payment_number", "invoice_id", "customer_id", "amount", "payment_method", "payment_date"]
    else:
        return {}
    data = {}
    for f in fields:
        value = getattr(obj, f)
        data[f] = float(value) if isinstance(value, Decimal) else (value.isoformat() if hasattr(value, "isoformat") else value)
    if isinstance(obj, Invoice):
        data.update(paid_amount=float(obj.paid_amount), balance=float(obj.balance))
    return data


def register_routes(app):
    @app.context_processor
    def globals():
        setting = BusinessSetting.query.first()
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count() if current_user.is_authenticated else 0
        return {"settings": setting, "unread_notifications": unread, "today": date.today(), "now": datetime.utcnow(), "Customer": Customer}

    @app.route("/")
    def index():
        return redirect(url_for("dashboard")) if current_user.is_authenticated else redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = User.query.filter_by(email=val("email").lower()).first()
            if user and user.is_active and user.check_password(request.form.get("password", "")):
                user.last_login = datetime.utcnow()
                db.session.commit()
                login_user(user, remember=bool(request.form.get("remember")))
                return redirect(request.args.get("next") or url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("auth/login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = val("email").lower()
            password = request.form.get("password", "")
            if User.query.filter_by(email=email).first():
                flash("Email is already registered.", "danger")
            elif len(password) < 8 or password != request.form.get("confirm_password"):
                flash("Use a matching password of at least 8 characters.", "danger")
            else:
                user = User(name=val("name"), email=email, phone=val("phone"), role="sales", email_verified=False)
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                otp = f"{secrets.randbelow(1000000):06d}"
                db.session.add(OTP(user_id=user.id, otp=otp, expires_at=datetime.utcnow() + timedelta(minutes=10)))
                db.session.commit()
                # Development-friendly flow: display OTP on the verification page.
                return render_template("auth/verify.html", email=email, dev_otp=otp)
        return render_template("auth/register.html")

    @app.route("/verify", methods=["POST"])
    def verify():
        user = User.query.filter_by(email=val("email").lower()).first()
        record = OTP.query.filter_by(user_id=user.id if user else 0, verified=False).order_by(OTP.id.desc()).first()
        if not user or not record or record.expires_at < datetime.utcnow() or record.attempts >= 5:
            flash("Verification code is invalid or expired.", "danger")
            return redirect(url_for("register"))
        record.attempts += 1
        if val("otp") != record.otp:
            db.session.commit()
            flash("Incorrect verification code.", "danger")
            return render_template("auth/verify.html", email=user.email)
        record.verified = True
        user.email_verified = True
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        invoices = Invoice.query.all()
        return render_template("index.html", stats={
            "leads": Lead.query.count(), "new_leads": Lead.query.filter_by(status="New").count(),
            "customers": Customer.query.count(), "quotations": Quotation.query.count(), "invoices": len(invoices),
            "revenue": sum((Decimal(str(i.total or 0)) for i in invoices), Decimal("0")),
            "paid": sum((i.paid_amount for i in invoices), Decimal("0")),
            "outstanding": sum((i.balance for i in invoices), Decimal("0")),
            "overdue": Invoice.query.filter_by(status="Overdue").count(),
        }, recent_leads=Lead.query.order_by(Lead.created_at.desc()).limit(5).all())

    @app.route("/leads", methods=["GET", "POST"])
    @login_required
    def leads():
        if request.method == "POST":
            lead = Lead(lead_number=next_number("LEAD", Lead), name=val("name"), company=val("company"),
                        email=val("email"), phone=val("phone"), source=val("source", "Website"),
                        status=val("status", "New"), priority=val("priority", "Medium"),
                        estimated_value=dec(val("estimated_value")), notes=val("notes"), assigned_to=current_user.id)
            if not lead.name:
                flash("Lead name is required.", "danger")
            else:
                db.session.add(lead)
                db.session.commit()
                flash("Lead created.", "success")
                return redirect(url_for("leads"))
        q = val("q")
        query = Lead.query
        if q:
            query = query.filter(db.or_(Lead.name.ilike(f"%{q}%"), Lead.company.ilike(f"%{q}%"), Lead.email.ilike(f"%{q}%")))
        return render_template("resource/list.html", title="Leads", resource="leads", items=query.order_by(Lead.created_at.desc()).all(),
                               columns=["lead_number", "name", "company", "status", "priority", "estimated_value"])

    @app.route("/leads/<int:lead_id>")
    @login_required
    def lead_detail(lead_id):
        return render_template("resource/detail.html", title="Lead", item=db.get_or_404(Lead, lead_id), resource="leads")

    @app.post("/leads/<int:lead_id>/convert")
    @login_required
    def convert_lead(lead_id):
        lead = db.get_or_404(Lead, lead_id)
        customer = Customer.query.filter((Customer.email == lead.email) | (Customer.phone == lead.phone)).first()
        if not customer:
            customer = Customer(customer_number=next_number("CUST", Customer), name=lead.name, company=lead.company,
                                email=lead.email, phone=lead.phone, notes=lead.notes)
            db.session.add(customer)
            db.session.flush()
        lead.status, lead.converted_customer_id, lead.converted_at = "Won", customer.id, datetime.utcnow()
        db.session.commit()
        flash("Lead converted to customer.", "success")
        return redirect(url_for("lead_detail", lead_id=lead.id))

    @app.route("/customers", methods=["GET", "POST"])
    @login_required
    def customers():
        if request.method == "POST":
            customer = Customer(customer_number=next_number("CUST", Customer), name=val("name"), company=val("company"),
                                email=val("email"), phone=val("phone"), address=val("address"), city=val("city"),
                                state=val("state"), pincode=val("pincode"), gstin=val("gstin"), pan=val("pan"))
            if not customer.name:
                flash("Customer name is required.", "danger")
            else:
                db.session.add(customer); db.session.commit(); flash("Customer created.", "success")
                return redirect(url_for("customers"))
        q = val("q")
        query = Customer.query
        if q:
            query = query.filter(db.or_(Customer.name.ilike(f"%{q}%"), Customer.company.ilike(f"%{q}%"), Customer.email.ilike(f"%{q}%")))
        return render_template("resource/list.html", title="Customers", resource="customers", items=query.order_by(Customer.created_at.desc()).all(),
                               columns=["customer_number", "name", "company", "email", "phone", "state"])

    @app.route("/products", methods=["GET", "POST"])
    @login_required
    def products():
        if request.method == "POST":
            product = Product(product_number=next_number("PROD", Product), name=val("name"), sku=val("sku"),
                              unit=val("unit", "PCS"), selling_price=dec(val("selling_price")),
                              purchase_price=dec(val("purchase_price")), tax_percentage=dec(val("tax_percentage"), "18"),
                              stock_quantity=dec(val("stock_quantity")), description=val("description"))
            if not product.name:
                flash("Product name is required.", "danger")
            else:
                db.session.add(product); db.session.commit(); flash("Product created.", "success")
                return redirect(url_for("products"))
        return render_template("resource/list.html", title="Products", resource="products", items=Product.query.order_by(Product.name).all(),
                               columns=["product_number", "name", "sku", "unit", "selling_price", "tax_percentage", "stock_quantity"])

    @app.route("/quotations", methods=["GET", "POST"])
    @login_required
    def quotations():
        if request.method == "POST":
            customer = db.session.get(Customer, request.form.get("customer_id"))
            if not customer:
                flash("Select a valid customer.", "danger")
            else:
                q = Quotation(quotation_number=next_number("QUO", Quotation), customer_id=customer.id,
                              quotation_date=parse_date(val("quotation_date"), date.today()), valid_until=parse_date(val("valid_until")),
                              salesperson_id=current_user.id, notes=val("notes"), terms=val("terms"))
                db.session.add(q); db.session.flush()
                list(document_items(request.form, QuotationItem, q.id))
                # form supports JSON items; a simple default line keeps UI usable.
                if not q.items:
                    db.session.add(QuotationItem(quotation=q, description="Professional service", quantity=1, rate=dec(val("rate"), "0"), tax=dec(val("tax"), "18")))
                db.session.flush(); calculate_document(q, QuotationItem); db.session.commit()
                flash("Quotation created.", "success"); return redirect(url_for("quotations"))
        return render_template("resource/list.html", title="Quotations", resource="quotations",
                               items=Quotation.query.order_by(Quotation.created_at.desc()).all(),
                               columns=["quotation_number", "customer", "status", "total", "quotation_date"])

    @app.route("/quotations/<int:quotation_id>/convert", methods=["POST"])
    @login_required
    def quotation_to_invoice(quotation_id):
        q = db.get_or_404(Quotation, quotation_id)
        invoice = Invoice(invoice_number=next_number("INV", Invoice), customer_id=q.customer_id, quotation_id=q.id,
                          invoice_date=date.today(), due_date=date.today() + timedelta(days=30), salesperson_id=current_user.id,
                          payment_terms="30 days", notes=q.notes, terms=q.terms)
        db.session.add(invoice); db.session.flush()
        for old in q.items:
            db.session.add(InvoiceItem(invoice_id=invoice.id, product_id=old.product_id, description=old.description, quantity=old.quantity,
                                       unit=old.unit, rate=old.rate, discount=old.discount, tax=old.tax))
        db.session.flush(); calculate_document(invoice, InvoiceItem); q.status = "Converted"; db.session.commit()
        return redirect(url_for("invoices"))

    @app.route("/invoices", methods=["GET", "POST"])
    @login_required
    def invoices():
        if request.method == "POST":
            customer = db.session.get(Customer, request.form.get("customer_id"))
            if not customer:
                flash("Select a valid customer.", "danger")
            else:
                inv = Invoice(invoice_number=next_number("INV", Invoice), customer_id=customer.id,
                              invoice_date=parse_date(val("invoice_date"), date.today()), due_date=parse_date(val("due_date")),
                              salesperson_id=current_user.id, payment_terms=val("payment_terms", "Due on receipt"), notes=val("notes"), terms=val("terms"))
                db.session.add(inv); db.session.flush(); list(document_items(request.form, InvoiceItem, inv.id))
                if not inv.items:
                    db.session.add(InvoiceItem(invoice=inv, description="Professional service", quantity=1, rate=dec(val("rate"), "0"), tax=dec(val("tax"), "18")))
                db.session.flush(); calculate_document(inv, InvoiceItem); db.session.commit()
                flash("Invoice created.", "success"); return redirect(url_for("invoices"))
        return render_template("resource/list.html", title="Invoices", resource="invoices",
                               items=Invoice.query.order_by(Invoice.created_at.desc()).all(),
                               columns=["invoice_number", "customer", "status", "total", "due_date"])

    @app.route("/invoices/<int:invoice_id>")
    @login_required
    def invoice_detail(invoice_id):
        return render_template("resource/detail.html", title="Invoice", item=db.get_or_404(Invoice, invoice_id), resource="invoices")

    @app.post("/invoices/<int:invoice_id>/payments")
    @login_required
    def record_payment(invoice_id):
        inv = db.get_or_404(Invoice, invoice_id)
        amount = dec(val("amount"))
        if amount <= 0 or amount > inv.balance:
            flash(f"Payment must be positive and no more than the balance ({inv.balance:.2f}).", "danger")
        else:
            payment = Payment(payment_number=next_number("PAY", Payment), invoice=inv, customer_id=inv.customer_id,
                              amount=amount, payment_method=val("payment_method", "Cash"), reference_number=val("reference_number"))
            db.session.add(payment); db.session.flush(); inv.refresh_status(); db.session.commit()
            flash("Payment recorded.", "success")
        return redirect(url_for("invoice_detail", invoice_id=inv.id))

    @app.route("/payments")
    @login_required
    def payments():
        return render_template("resource/list.html", title="Payments", resource="payments",
                               items=Payment.query.order_by(Payment.created_at.desc()).all(),
                               columns=["payment_number", "invoice", "customer", "amount", "payment_method", "payment_date"])

    @app.route("/reports")
    @login_required
    def reports():
        invoices = Invoice.query.all()
        return render_template("reports/index.html", invoices=invoices, totals={
            "sales": sum((Decimal(str(i.total or 0)) for i in invoices), Decimal("0")),
            "paid": sum((i.paid_amount for i in invoices), Decimal("0")),
            "balance": sum((i.balance for i in invoices), Decimal("0")),
        })

    @app.route("/tasks")
    @login_required
    def tasks():
        return render_template("resource/list.html", title="Tasks", resource="tasks",
                               items=Task.query.order_by(Task.due_date.asc().nullslast()).all(),
                               columns=["title", "status", "priority", "due_date"])

    @app.route("/followups")
    @login_required
    def followups():
        return render_template("resource/list.html", title="Follow-ups", resource="followups",
                               items=FollowUp.query.order_by(FollowUp.followup_date.asc()).all(),
                               columns=["followup_date", "type", "status", "notes"])

    @app.route("/users")
    @role_required("admin")
    def users():
        return render_template("resource/list.html", title="Users", resource="users",
                               items=User.query.order_by(User.created_at.desc()).all(),
                               columns=["name", "email", "role", "is_active", "created_at"])

    @app.post("/notifications/<int:notification_id>/read")
    @login_required
    def mark_notification_read(notification_id):
        notification = db.session.get(Notification, notification_id)
        if notification and notification.user_id == current_user.id:
            notification.is_read = True
            db.session.commit()
        return redirect(request.referrer or url_for("dashboard"))

    @app.route("/settings", methods=["GET", "POST"])
    @role_required("admin")
    def settings_page():
        setting = BusinessSetting.query.first() or BusinessSetting()
        if request.method == "POST":
            for field in ["business_name", "email", "phone", "address", "city", "state", "pincode", "gstin", "pan",
                          "website", "invoice_prefix", "quotation_prefix", "currency", "payment_terms", "invoice_notes", "terms"]:
                setattr(setting, field, val(field, getattr(setting, field) or ""))
            setting.default_tax_rate = dec(val("default_tax_rate"), "18")
            db.session.add(setting); db.session.commit(); flash("Settings saved.", "success")
        return render_template("settings/index.html", setting=setting)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            current_user.name, current_user.phone = val("name"), val("phone")
            if request.form.get("password"):
                if len(request.form["password"]) < 8:
                    flash("Password must be at least 8 characters.", "danger")
                else:
                    current_user.set_password(request.form["password"])
            db.session.commit(); flash("Profile updated.", "success")
        return render_template("settings/profile.html")

    @app.route("/api/dashboard")
    @login_required
    def api_dashboard():
        invoices = Invoice.query.all()
        return jsonify(leads=Lead.query.count(), customers=Customer.query.count(), invoices=len(invoices),
                       revenue=float(sum((Decimal(str(i.total or 0)) for i in invoices), Decimal("0"))),
                       paid=float(sum((i.paid_amount for i in invoices), Decimal("0"))))

    api_models = {"leads": Lead, "customers": Customer, "products": Product, "quotations": Quotation, "invoices": Invoice, "payments": Payment}
    @app.route("/api/<resource>", methods=["GET", "POST"])
    @login_required
    def api_collection(resource):
        model = api_models.get(resource)
        if not model:
            abort(404)
        if request.method == "GET":
            return jsonify([serialize(x) for x in model.query.order_by(model.id.desc()).all()])
        data = request.get_json(silent=True) or {}
        if model is Lead:
            obj = Lead(lead_number=next_number("LEAD", Lead), name=data.get("name", ""), company=data.get("company"),
                       email=data.get("email"), phone=data.get("phone"), source=data.get("source", "Website"),
                       status=data.get("status", "New"), priority=data.get("priority", "Medium"), estimated_value=dec(data.get("estimated_value")))
        elif model is Customer:
            obj = Customer(customer_number=next_number("CUST", Customer), name=data.get("name", ""), company=data.get("company"), email=data.get("email"), phone=data.get("phone"))
        elif model is Product:
            obj = Product(product_number=next_number("PROD", Product), name=data.get("name", ""), sku=data.get("sku"), selling_price=dec(data.get("selling_price")), tax_percentage=dec(data.get("tax_percentage"), "18"))
        elif model is Quotation:
            customer = db.session.get(Customer, data.get("customer_id"))
            if not customer:
                return jsonify(error="customer_id is required"), 400
            obj = Quotation(quotation_number=next_number("QUO", Quotation), customer_id=customer.id,
                            salesperson_id=current_user.id, quotation_date=parse_date(data.get("quotation_date"), date.today()),
                            valid_until=parse_date(data.get("valid_until")), notes=data.get("notes"), terms=data.get("terms"))
            db.session.add(obj); db.session.flush()
            list(document_items(data, QuotationItem, obj.id))
            db.session.flush(); calculate_document(obj, QuotationItem)
        elif model is Invoice:
            customer = db.session.get(Customer, data.get("customer_id"))
            if not customer:
                return jsonify(error="customer_id is required"), 400
            obj = Invoice(invoice_number=next_number("INV", Invoice), customer_id=customer.id,
                          salesperson_id=current_user.id, invoice_date=parse_date(data.get("invoice_date"), date.today()),
                          due_date=parse_date(data.get("due_date")), payment_terms=data.get("payment_terms", "Due on receipt"))
            db.session.add(obj); db.session.flush()
            list(document_items(data, InvoiceItem, obj.id))
            db.session.flush(); calculate_document(obj, InvoiceItem)
        elif model is Payment:
            invoice = db.session.get(Invoice, data.get("invoice_id"))
            amount = dec(data.get("amount"))
            if not invoice or amount <= 0 or amount > invoice.balance:
                return jsonify(error="payment exceeds invoice balance or is invalid"), 400
            obj = Payment(payment_number=next_number("PAY", Payment), invoice=invoice,
                         customer_id=invoice.customer_id, amount=amount,
                         payment_method=data.get("payment_method", "Cash"),
                         reference_number=data.get("reference_number"))
            db.session.add(obj); db.session.flush(); invoice.refresh_status()
        else:
            return jsonify(error="Use the web form for document creation"), 400
        if model in (Lead, Customer, Product) and not getattr(obj, "name", ""):
            return jsonify(error="name is required"), 400
        db.session.add(obj); db.session.commit()
        return jsonify(serialize(obj)), 201

    @app.route("/api/<resource>/<int:item_id>", methods=["GET", "PUT", "DELETE"])
    @login_required
    def api_item(resource, item_id):
        model = api_models.get(resource)
        if not model:
            abort(404)
        obj = db.session.get(model, item_id) or abort(404)
        if request.method == "GET":
            return jsonify(serialize(obj))
        if request.method == "DELETE":
            db.session.delete(obj); db.session.commit(); return "", 204
        data = request.get_json(silent=True) or {}
        for field in ["name", "company", "email", "phone", "status", "priority", "source", "sku", "selling_price", "tax_percentage"]:
            if field in data and hasattr(obj, field):
                setattr(obj, field, dec(data[field]) if field in ("selling_price", "tax_percentage") else data[field])
        db.session.commit()
        return jsonify(serialize(obj))

    @app.route("/api/reports/summary")
    @login_required
    def api_report_summary():
        invoices = Invoice.query.all()
        return jsonify(total_invoices=len(invoices), total_sales=float(sum((Decimal(str(i.total or 0)) for i in invoices), Decimal("0"))),
                       total_paid=float(sum((i.paid_amount for i in invoices), Decimal("0"))),
                       outstanding=float(sum((i.balance for i in invoices), Decimal("0"))),
                       lead_conversion_rate=round(Lead.query.filter_by(status="Won").count() / max(Lead.query.count(), 1) * 100, 2))

    @app.route("/export/<resource>.csv")
    @login_required
    def export_csv(resource):
        model = api_models.get(resource)
        if not model:
            abort(404)
        output = io.StringIO()
        rows = [serialize(x) for x in model.query.all()]
        fields = list(rows[0].keys()) if rows else ["id"]
        writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={resource}.csv"
        response.headers["Content-Type"] = "text/csv"
        return response

    @app.route("/pdf/<resource>/<int:item_id>")
    @login_required
    def pdf(resource, item_id):
        model = {"quotations": Quotation, "invoices": Invoice}.get(resource)
        if not model:
            abort(404)
        obj = db.session.get(model, item_id) or abort(404)
        stream = io.BytesIO()
        doc = SimpleDocTemplate(stream, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm)
        styles = getSampleStyleSheet()
        story = [Paragraph(f"<b>{settings_name()}</b>", styles["Title"]), Paragraph(f"{resource.title()} {obj.quotation_number if isinstance(obj, Quotation) else obj.invoice_number}", styles["Heading2"])]
        story += [Spacer(1, 8), Paragraph(f"Customer: {obj.customer.name} | Date: {getattr(obj, 'quotation_date', getattr(obj, 'invoice_date', date.today()))}", styles["Normal"])]
        rows = [["Description", "Qty", "Rate", "Tax", "Amount"]]
        for item in obj.items:
            rows.append([item.description or "", str(item.quantity), str(item.rate), f"{item.tax}%", f"{item.amount}"])
        rows.append(["", "", "", "Total", str(obj.total)])
        table = Table(rows, colWidths=[75*mm, 20*mm, 25*mm, 20*mm, 30*mm])
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172554")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
        story += [table, Spacer(1, 12), Paragraph(f"Notes: {obj.notes or ''}", styles["Normal"])]
        doc.build(story)
        response = make_response(stream.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"inline; filename={resource}-{item_id}.pdf"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return render_template("errors/error.html", code=error.code, message=error.description), error.code

    @app.errorhandler(Exception)
    def server_error(error):
        app.logger.exception("Unhandled error")
        return render_template("errors/error.html", code=500, message="Something went wrong. Please try again."), 500


def settings_name():
    setting = BusinessSetting.query.first()
    return setting.business_name if setting else "LeadFlow CRM"


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_ENV") == "development")
