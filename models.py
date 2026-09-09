<<<<<<< HEAD
from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="sales", nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)

    def set_password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)


class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    otp = db.Column(db.String(128), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_number = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(160))
    email = db.Column(db.String(160))
    phone = db.Column(db.String(30))
    alternate_phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(12))
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(20))
    notes = db.Column(db.Text)


class Lead(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_number = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(160))
    email = db.Column(db.String(160))
    phone = db.Column(db.String(30))
    alternate_phone = db.Column(db.String(30))
    source = db.Column(db.String(40), default="Website")
    status = db.Column(db.String(30), default="New")
    priority = db.Column(db.String(20), default="Medium")
    estimated_value = db.Column(db.Numeric(12, 2), default=0)
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    converted_customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    converted_at = db.Column(db.DateTime)
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    customer = db.relationship("Customer", foreign_keys=[converted_customer_id])


class Product(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_number = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    sku = db.Column(db.String(80))
    description = db.Column(db.Text)
    category = db.Column(db.String(80))
    unit = db.Column(db.String(20), default="PCS")
    purchase_price = db.Column(db.Numeric(12, 2), default=0)
    selling_price = db.Column(db.Numeric(12, 2), default=0)
    tax_percentage = db.Column(db.Numeric(5, 2), default=18)
    stock_quantity = db.Column(db.Numeric(12, 2), default=0)
    low_stock_threshold = db.Column(db.Numeric(12, 2), default=5)
    active = db.Column(db.Boolean, default=True)


class Quotation(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(40), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    quotation_date = db.Column(db.Date, default=date.today)
    valid_until = db.Column(db.Date)
    salesperson_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20), default="Draft")
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount_total = db.Column(db.Numeric(12, 2), default=0)
    tax_total = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    customer = db.relationship("Customer", backref=db.backref("quotations", lazy=True))
    items = db.relationship("QuotationItem", backref="quotation", cascade="all, delete-orphan")


class QuotationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotation.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Numeric(12, 2), default=1)
    unit = db.Column(db.String(20), default="PCS")
    rate = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(5, 2), default=0)
    tax = db.Column(db.Numeric(5, 2), default=0)
    amount = db.Column(db.Numeric(12, 2), default=0)
    product = db.relationship("Product")


class Invoice(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotation.id"))
    invoice_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date)
    salesperson_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    payment_terms = db.Column(db.String(80), default="Due on receipt")
    status = db.Column(db.String(25), default="Draft")
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount_total = db.Column(db.Numeric(12, 2), default=0)
    tax_total = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    customer = db.relationship("Customer", backref=db.backref("invoices", lazy=True))
    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan")

    @property
    def paid_amount(self):
        return sum((Decimal(str(p.amount or 0)) for p in self.payments), Decimal("0"))

    @property
    def balance(self):
        return max(Decimal("0"), Decimal(str(self.total or 0)) - self.paid_amount)

    def refresh_status(self):
        if self.status == "Cancelled":
            return
        if self.balance <= 0 and self.total:
            self.status = "Paid"
        elif self.paid_amount > 0:
            self.status = "Partially Paid"
        elif self.due_date and self.due_date < date.today() and self.total:
            self.status = "Overdue"


class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Numeric(12, 2), default=1)
    unit = db.Column(db.String(20), default="PCS")
    rate = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(5, 2), default=0)
    tax = db.Column(db.Numeric(5, 2), default=0)
    amount = db.Column(db.Numeric(12, 2), default=0)
    product = db.relationship("Product")


class Payment(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(40), unique=True, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(30), default="Cash")
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    customer = db.relationship("Customer", backref=db.backref("payments", lazy=True))


class FollowUp(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"))
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    followup_date = db.Column(db.Date, nullable=False)
    followup_time = db.Column(db.Time)
    type = db.Column(db.String(30), default="Call")
    status = db.Column(db.String(20), default="Pending")
    notes = db.Column(db.Text)


class Task(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(20), default="Pending")


class BusinessSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    business_name = db.Column(db.String(160), default="LeadFlow CRM")
    email = db.Column(db.String(160), default="hello@leadflow.local")
    phone = db.Column(db.String(40))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(12))
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(20))
    website = db.Column(db.String(160))
    invoice_prefix = db.Column(db.String(10), default="INV")
    quotation_prefix = db.Column(db.String(10), default="QUO")
    currency = db.Column(db.String(10), default="INR")
    default_tax_rate = db.Column(db.Numeric(5, 2), default=18)
    payment_terms = db.Column(db.String(80), default="Due on receipt")
    invoice_notes = db.Column(db.Text)
    terms = db.Column(db.Text)


class Notification(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)


def calculate_item(quantity, rate, discount, tax):
    quantity, rate = Decimal(str(quantity or 0)), Decimal(str(rate or 0))
    discount, tax = Decimal(str(discount or 0)), Decimal(str(tax or 0))
    gross = quantity * rate
    discount_amount = gross * discount / Decimal("100")
    taxable = gross - discount_amount
    tax_amount = taxable * tax / Decimal("100")
    return gross, discount_amount, tax_amount, taxable + tax_amount
=======
from datetime import datetime, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="sales", nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)

    def set_password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)


class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    otp = db.Column(db.String(128), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_number = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(160))
    email = db.Column(db.String(160))
    phone = db.Column(db.String(30))
    alternate_phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(12))
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(20))
    notes = db.Column(db.Text)


class Lead(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_number = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(160))
    email = db.Column(db.String(160))
    phone = db.Column(db.String(30))
    alternate_phone = db.Column(db.String(30))
    source = db.Column(db.String(40), default="Website")
    status = db.Column(db.String(30), default="New")
    priority = db.Column(db.String(20), default="Medium")
    estimated_value = db.Column(db.Numeric(12, 2), default=0)
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    notes = db.Column(db.Text)
    converted_customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    converted_at = db.Column(db.DateTime)
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    customer = db.relationship("Customer", foreign_keys=[converted_customer_id])


class Product(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_number = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    sku = db.Column(db.String(80))
    description = db.Column(db.Text)
    category = db.Column(db.String(80))
    unit = db.Column(db.String(20), default="PCS")
    purchase_price = db.Column(db.Numeric(12, 2), default=0)
    selling_price = db.Column(db.Numeric(12, 2), default=0)
    tax_percentage = db.Column(db.Numeric(5, 2), default=18)
    stock_quantity = db.Column(db.Numeric(12, 2), default=0)
    low_stock_threshold = db.Column(db.Numeric(12, 2), default=5)
    active = db.Column(db.Boolean, default=True)


class Quotation(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(40), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    quotation_date = db.Column(db.Date, default=date.today)
    valid_until = db.Column(db.Date)
    salesperson_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20), default="Draft")
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount_total = db.Column(db.Numeric(12, 2), default=0)
    tax_total = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    customer = db.relationship("Customer", backref=db.backref("quotations", lazy=True))
    items = db.relationship("QuotationItem", backref="quotation", cascade="all, delete-orphan")


class QuotationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotation.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Numeric(12, 2), default=1)
    unit = db.Column(db.String(20), default="PCS")
    rate = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(5, 2), default=0)
    tax = db.Column(db.Numeric(5, 2), default=0)
    amount = db.Column(db.Numeric(12, 2), default=0)
    product = db.relationship("Product")


class Invoice(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotation.id"))
    invoice_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date)
    salesperson_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    payment_terms = db.Column(db.String(80), default="Due on receipt")
    status = db.Column(db.String(25), default="Draft")
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    discount_total = db.Column(db.Numeric(12, 2), default=0)
    tax_total = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    customer = db.relationship("Customer", backref=db.backref("invoices", lazy=True))
    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan")

    @property
    def paid_amount(self):
        return sum((Decimal(str(p.amount or 0)) for p in self.payments), Decimal("0"))

    @property
    def balance(self):
        return max(Decimal("0"), Decimal(str(self.total or 0)) - self.paid_amount)

    def refresh_status(self):
        if self.status == "Cancelled":
            return
        if self.balance <= 0 and self.total:
            self.status = "Paid"
        elif self.paid_amount > 0:
            self.status = "Partially Paid"
        elif self.due_date and self.due_date < date.today() and self.total:
            self.status = "Overdue"


class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Numeric(12, 2), default=1)
    unit = db.Column(db.String(20), default="PCS")
    rate = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(5, 2), default=0)
    tax = db.Column(db.Numeric(5, 2), default=0)
    amount = db.Column(db.Numeric(12, 2), default=0)
    product = db.relationship("Product")


class Payment(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(40), unique=True, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(30), default="Cash")
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    customer = db.relationship("Customer", backref=db.backref("payments", lazy=True))


class FollowUp(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"))
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    followup_date = db.Column(db.Date, nullable=False)
    followup_time = db.Column(db.Time)
    type = db.Column(db.String(30), default="Call")
    status = db.Column(db.String(20), default="Pending")
    notes = db.Column(db.Text)


class Task(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(20), default="Pending")


class BusinessSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    business_name = db.Column(db.String(160), default="LeadFlow CRM")
    email = db.Column(db.String(160), default="hello@leadflow.local")
    phone = db.Column(db.String(40))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(12))
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(20))
    website = db.Column(db.String(160))
    invoice_prefix = db.Column(db.String(10), default="INV")
    quotation_prefix = db.Column(db.String(10), default="QUO")
    currency = db.Column(db.String(10), default="INR")
    default_tax_rate = db.Column(db.Numeric(5, 2), default=18)
    payment_terms = db.Column(db.String(80), default="Due on receipt")
    invoice_notes = db.Column(db.Text)
    terms = db.Column(db.Text)


class Notification(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)


def calculate_item(quantity, rate, discount, tax):
    quantity, rate = Decimal(str(quantity or 0)), Decimal(str(rate or 0))
    discount, tax = Decimal(str(discount or 0)), Decimal(str(tax or 0))
    gross = quantity * rate
    discount_amount = gross * discount / Decimal("100")
    taxable = gross - discount_amount
    tax_amount = taxable * tax / Decimal("100")
    return gross, discount_amount, tax_amount, taxable + tax_amount
>>>>>>> 49f8c2b7fdd2a180ec0cc017c4dffa4fe1c3a8ea
