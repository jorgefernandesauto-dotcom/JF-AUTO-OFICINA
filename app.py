
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash
import os
import shutil
import traceback

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "oficina-pro-chave-mude-em-producao")
# A base de dados fica sempre na pasta do programa, independentemente de onde o servidor é iniciado.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "oficina.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE.replace(os.sep, "/")}")
# Alguns fornecedores devolvem postgres://; SQLAlchemy moderno usa postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

VAT_DEFAULT = 23.0

# Backup simples da base de dados para proteção dos dados.
# É criado ao iniciar o programa, sem substituir o ficheiro principal.
def backup_database():
    try:
        if os.path.exists(DB_FILE):
            backup_dir = os.path.join(BASE_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(DB_FILE, os.path.join(backup_dir, f"oficina_{stamp}.db"))
    except Exception:
        pass



class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    nif = db.Column(db.String(30))
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    address = db.Column(db.String(250))
    notes = db.Column(db.Text)
    vehicles = db.relationship("Vehicle", backref="client", cascade="all, delete-orphan")

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), nullable=False, index=True)
    brand = db.Column(db.String(80))
    model = db.Column(db.String(80))
    year = db.Column(db.Integer)
    vin = db.Column(db.String(80))
    km = db.Column(db.Integer, default=0)
    fuel = db.Column(db.String(30))
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    work_orders = db.relationship("WorkOrder", backref="vehicle", cascade="all, delete-orphan")

class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    description = db.Column(db.String(160), nullable=False)
    supplier = db.Column(db.String(120))
    purchase_price = db.Column(db.Float, default=0)
    sale_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)
    active = db.Column(db.Boolean, default=True)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(250))
    sale_price = db.Column(db.Float, default=0)
    cost_price = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)
    active = db.Column(db.Boolean, default=True)

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(db.String(40), default="Aberta")
    complaint = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    work_done = db.Column(db.Text)
    mechanic = db.Column(db.String(120))
    entry_at = db.Column(db.DateTime, default=datetime.utcnow)
    exit_at = db.Column(db.DateTime)
    km = db.Column(db.Integer, default=0)
    discount = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    items = db.relationship("WorkItem", backref="order", cascade="all, delete-orphan")

class WorkItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("work_order.id"), nullable=False)
    item_type = db.Column(db.String(20), default="Peça")  # Peça / Mão de obra
    description = db.Column(db.String(250), nullable=False)
    reference = db.Column(db.String(80))
    quantity = db.Column(db.Float, default=1)
    unit_price = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime)
    client_name = db.Column(db.String(150), nullable=False)
    plate = db.Column(db.String(20))
    service = db.Column(db.String(200))
    mechanic = db.Column(db.String(120))
    status = db.Column(db.String(40), default="Marcada")

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(db.String(30), default="Pendente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.Date)
    notes = db.Column(db.Text)
    discount = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"), nullable=False)
    vehicle = db.relationship("Vehicle")
    stock_applied = db.Column(db.Boolean, default=False)
    items = db.relationship("QuoteItem", backref="quote", cascade="all, delete-orphan")

class QuoteItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quote.id"), nullable=False)
    item_type = db.Column(db.String(20), default="Peça")
    description = db.Column(db.String(250), nullable=False)
    reference = db.Column(db.String(80))
    quantity = db.Column(db.Float, default=1)
    unit_price = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(db.String(30), default="Emitida")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    discount = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicle.id"))
    client = db.relationship("Client")
    vehicle = db.relationship("Vehicle")
    stock_applied = db.Column(db.Boolean, default=False)
    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan")

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    item_type = db.Column(db.String(20), default="Peça")
    description = db.Column(db.String(250), nullable=False)
    reference = db.Column(db.String(80))
    quantity = db.Column(db.Float, default=1)
    unit_price = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    vat = db.Column(db.Float, default=VAT_DEFAULT)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), default="JF Auto Mecânica")
    nif = db.Column(db.String(30), default="")
    phone = db.Column(db.String(40), default="")
    email = db.Column(db.String(120), default="")
    address = db.Column(db.String(250), default="")
    vat = db.Column(db.Float, default=VAT_DEFAULT)

def item_net(i):
    return max(0, (i.quantity or 0) * (i.unit_price or 0) - (i.discount or 0))
def totals(items, discount=0, vat=VAT_DEFAULT):
    subtotal = sum(item_net(i) for i in items)
    taxable = max(0, subtotal - (discount or 0))
    iva = taxable * (vat or 0) / 100
    return subtotal, max(0, discount or 0), iva, taxable + iva

@app.template_filter("eur")
def eur(v):
    return f"{(v or 0):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

@app.context_processor
def globals():
    settings = Setting.query.first()
    return {"now": datetime.now(), "settings": settings, "item_net": item_net, "totals": totals}


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    # Regista o erro completo para podermos corrigir qualquer problema restante.
    try:
        log_file = os.path.join(BASE_DIR, "erro.log")
        with open(log_file, "a", encoding="utf-8") as log:
            log.write("\n\n" + "="*80 + "\n")
            log.write(datetime.now().isoformat() + "\n")
            log.write(request.method + " " + request.path + "\n")
            log.write(traceback.format_exc())
    except Exception:
        pass
    db.session.rollback()
    return render_template("error.html", error=str(error)), 500


def apply_stock(items, reverse=False):
    """Aplica ou desfaz movimentos de stock para itens do tipo Peça."""
    for i in items:
        if (i.item_type or "").strip().lower() != "peça":
            continue
        if not i.reference:
            continue
        p = Part.query.filter_by(code=i.reference).first()
        if not p:
            continue
        qty = float(i.quantity or 0)
        p.quantity = int(round((p.quantity or 0) + (qty if reverse else -qty)))
        if p.quantity < 0:
            raise ValueError(f"Stock insuficiente para {p.description}. Disponível: {p.quantity + int(round(qty))}")

def set_quote_status(q, new_status):
    old = q.status
    if old != "Convertido" and new_status == "Convertido":
        if not q.stock_applied:
            apply_stock(q.items)
            q.stock_applied = True
    elif old == "Convertido" and new_status != "Convertido":
        if q.stock_applied:
            apply_stock(q.items, reverse=True)
            q.stock_applied = False
    q.status = new_status

@app.before_request
def require_login():
    if request.endpoint in {"login", "logout", "health", "static"}:
        return
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, active=True).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear(); session["user_id"] = user.id; session["username"] = user.username
            return redirect(request.args.get("next") or request.form.get("next") or url_for("dashboard"))
        flash("Utilizador ou palavra-passe incorretos.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/settings/password", methods=["POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = db.session.get(User, session["user_id"])
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    if not user or not check_password_hash(user.password_hash, current):
        flash("A palavra-passe atual está incorreta.")
    elif len(new) < 8:
        flash("A nova palavra-passe deve ter pelo menos 8 caracteres.")
    else:
        user.password_hash = generate_password_hash(new)
        db.session.commit(); flash("Palavra-passe alterada com sucesso.")
    return redirect(url_for("settings"))

@app.route("/")
def dashboard():
    today = date.today()
    open_orders = WorkOrder.query.filter(WorkOrder.status != "Entregue").count()
    low_stock = Part.query.filter(Part.quantity <= Part.minimum_stock, Part.active == True).count()
    month_start = datetime(today.year, today.month, 1)
    month_orders = WorkOrder.query.filter(WorkOrder.entry_at >= month_start).all()
    revenue = sum(totals(o.items, o.discount, o.vat)[3] for o in month_orders)
    quotes_pending = Quote.query.filter_by(status="Pendente").count()
    appointments = Appointment.query.filter(Appointment.start_at >= datetime.now()).order_by(Appointment.start_at).limit(8).all()
    return render_template("dashboard.html", clients=Client.query.count(), vehicles=Vehicle.query.count(),
                           open_orders=open_orders, low_stock=low_stock, revenue=revenue,
                           quotes_pending=quotes_pending, appointments=appointments)

@app.route("/clients")
def clients():
    q = request.args.get("q", "").strip()
    query = Client.query
    if q:
        query = query.filter(or_(Client.name.ilike(f"%{q}%"), Client.nif.ilike(f"%{q}%"), Client.phone.ilike(f"%{q}%")))
    return render_template("clients.html", clients=query.order_by(Client.name).all(), q=q)

@app.route("/clients/new", methods=["GET","POST"])
def new_client():
    if request.method == "POST":
        c = Client(name=request.form["name"].strip(), nif=request.form.get("nif"), phone=request.form.get("phone"),
                   email=request.form.get("email"), address=request.form.get("address"), notes=request.form.get("notes"))
        db.session.add(c); db.session.commit(); flash("Cliente criado.")
        return redirect(url_for("clients"))
    return render_template("client_form.html")

@app.route("/vehicles")
def vehicles():
    q = request.args.get("q", "").strip()
    query = Vehicle.query
    if q:
        query = query.filter(or_(Vehicle.plate.ilike(f"%{q}%"), Vehicle.brand.ilike(f"%{q}%"), Vehicle.model.ilike(f"%{q}%")))
    return render_template("vehicles.html", vehicles=query.order_by(Vehicle.plate).all(), q=q)

@app.route("/vehicles/new", methods=["GET","POST"])
def new_vehicle():
    clients = Client.query.order_by(Client.name).all()
    if request.method == "POST":
        v = Vehicle(plate=request.form["plate"].upper().strip(), brand=request.form.get("brand"), model=request.form.get("model"),
                    year=int(request.form["year"]) if request.form.get("year") else None, vin=request.form.get("vin"),
                    km=int(request.form.get("km") or 0), fuel=request.form.get("fuel"), client_id=int(request.form["client_id"]))
        db.session.add(v); db.session.commit(); flash("Viatura criada.")
        return redirect(url_for("vehicles"))
    return render_template("vehicle_form.html", clients=clients)

def next_number(prefix, model):
    y = datetime.now().year
    count = model.query.filter(model.number.like(f"{prefix}-{y}-%")).count() + 1
    return f"{prefix}-{y}-{count:05d}"

@app.route("/orders")
def orders():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = WorkOrder.query
    if status: query = query.filter_by(status=status)
    if q:
        query = query.join(Vehicle).filter(or_(WorkOrder.number.ilike(f"%{q}%"), Vehicle.plate.ilike(f"%{q}%")))
    return render_template("orders.html", orders=query.order_by(WorkOrder.id.desc()).all(), q=q, status=status)

@app.route("/orders/new", methods=["GET","POST"])
def new_order():
    vehicles = Vehicle.query.order_by(Vehicle.plate).all()
    parts = Part.query.filter_by(active=True).order_by(Part.description).all()
    services = Service.query.filter_by(active=True).order_by(Service.name).all()
    if request.method == "POST":
        n = next_number("OR", WorkOrder)
        o = WorkOrder(number=n, vehicle_id=int(request.form["vehicle_id"]), complaint=request.form.get("complaint"),
                      mechanic=request.form.get("mechanic"), km=int(request.form.get("km") or 0),
                      vat=float(request.form.get("vat") or VAT_DEFAULT), discount=float(request.form.get("discount") or 0))
        db.session.add(o); db.session.flush()
        add_posted_items(o, "item")
        db.session.commit(); flash(f"Ordem {n} criada.")
        return redirect(url_for("order_detail", id=o.id))
    return render_template("order_form.html", vehicles=vehicles, parts=parts, services=services)

def add_posted_items(parent, prefix):
    descs = request.form.getlist(f"{prefix}_description[]")
    refs = request.form.getlist(f"{prefix}_reference[]")
    types = request.form.getlist(f"{prefix}_type[]")
    qtys = request.form.getlist(f"{prefix}_quantity[]")
    prices = request.form.getlist(f"{prefix}_price[]")
    vats = request.form.getlist(f"{prefix}_vat[]")
    for d,r,t,q,p,v in zip(descs, refs, types, qtys, prices, vats):
        if not d.strip(): continue
        parent.items.append(WorkItem(description=d.strip(), reference=r, item_type=t or "Peça",
                                     quantity=float(q or 1), unit_price=float(p or 0), vat=float(v or VAT_DEFAULT)))

@app.route("/orders/<int:id>")
def order_detail(id):
    o = WorkOrder.query.get_or_404(id)
    return render_template("order_detail.html", o=o, vehicles=Vehicle.query.order_by(Vehicle.plate).all(), totals=totals(o.items, o.discount, o.vat))

@app.route("/orders/<int:id>/update", methods=["POST"])
def order_update(id):
    o=WorkOrder.query.get_or_404(id)
    o.status=request.form.get("status",o.status); o.mechanic=request.form.get("mechanic")
    if request.form.get("vehicle_id"): o.vehicle_id=int(request.form["vehicle_id"])
    o.km=int(float(request.form.get("km") or o.km or 0)); o.complaint=request.form.get("complaint")
    o.diagnosis=request.form.get("diagnosis"); o.work_done=request.form.get("work_done")
    o.discount=float(request.form.get("discount") or 0); o.vat=float(request.form.get("vat") or VAT_DEFAULT)
    if o.status=="Entregue" and not o.exit_at: o.exit_at=datetime.utcnow()
    db.session.commit(); flash("Ordem atualizada."); return redirect(url_for("order_detail",id=id))

@app.route("/orders/<int:id>/item", methods=["POST"])
def order_item(id):
    o=WorkOrder.query.get_or_404(id)
    i=WorkItem(order_id=o.id, item_type=request.form.get("item_type","Peça"), description=request.form["description"],
               reference=request.form.get("reference"), quantity=float(request.form.get("quantity") or 1),
               unit_price=float(request.form.get("unit_price") or 0), vat=float(request.form.get("vat") or o.vat))
    o.items.append(i); db.session.commit(); return redirect(url_for("order_detail",id=id))

@app.route("/orders/<int:id>/item/<int:item_id>/edit", methods=["POST"])
def order_item_edit(id,item_id):
    i=WorkItem.query.filter_by(id=item_id,order_id=id).first_or_404()
    i.item_type=request.form.get("item_type","Peça"); i.description=request.form["description"].strip()
    i.quantity=float(request.form.get("quantity") or 1); i.unit_price=float(request.form.get("unit_price") or 0)
    db.session.commit(); flash("Item da ordem alterado.")
    return redirect(url_for("order_detail",id=id))

@app.route("/orders/<int:id>/item/<int:item_id>/delete", methods=["POST"])
def order_item_delete(id,item_id):
    i=WorkItem.query.filter_by(id=item_id,order_id=id).first_or_404()
    db.session.delete(i); db.session.commit(); return redirect(url_for("order_detail",id=id))

@app.route("/orders/<int:id>/print")
def order_print(id):
    o=WorkOrder.query.get_or_404(id)
    return render_template("order_print.html", o=o, totals=totals(o.items,o.discount,o.vat))

@app.route("/quotes")
def quotes():
    return render_template("quotes.html", quotes=Quote.query.order_by(Quote.id.desc()).all())

@app.route("/quotes/new", methods=["GET","POST"])
def new_quote():
    vehicles=Vehicle.query.order_by(Vehicle.plate).all()
    parts=Part.query.filter_by(active=True).order_by(Part.description).all()
    services=Service.query.filter_by(active=True).order_by(Service.name).all()
    if request.method=="POST":
        q=Quote(number=next_number("OC",Quote), vehicle_id=int(request.form["vehicle_id"]),
                valid_until=datetime.fromisoformat(request.form["valid_until"]).date() if request.form.get("valid_until") else None,
                notes=request.form.get("notes"), vat=float(request.form.get("vat") or VAT_DEFAULT),
                discount=float(request.form.get("discount") or 0))
        db.session.add(q); db.session.flush()
        descs=request.form.getlist("item_description[]"); refs=request.form.getlist("item_reference[]")
        types=request.form.getlist("item_type[]"); qtys=request.form.getlist("item_quantity[]")
        prices=request.form.getlist("item_price[]")
        for d,r,t,qty,p in zip(descs,refs,types,qtys,prices):
            if d.strip(): q.items.append(QuoteItem(item_type=t or "Peça",description=d.strip(),reference=r,quantity=float(qty or 1),unit_price=float(p or 0),vat=q.vat))
        db.session.commit(); flash(f"Orçamento {q.number} criado.")
        return redirect(url_for("quote_detail",id=q.id))
    return render_template("quote_form.html", vehicles=vehicles,parts=parts,services=services)

@app.route("/quotes/<int:id>")
def quote_detail(id):
    q=Quote.query.get_or_404(id)
    return render_template("quote_detail.html", q=q, totals=totals(q.items,q.discount,q.vat))

@app.route("/quotes/<int:id>/status", methods=["POST"])
def quote_status(id):
    q=Quote.query.get_or_404(id)
    try:
        set_quote_status(q, request.form["status"])
        db.session.commit()
        flash("Estado do orçamento atualizado.")
    except ValueError as e:
        db.session.rollback()
        flash(str(e))
    return redirect(url_for("quote_detail",id=id))

@app.route("/quotes/<int:id>/edit", methods=["GET","POST"])
def quote_edit(id):
    q=Quote.query.get_or_404(id)
    vehicles=Vehicle.query.order_by(Vehicle.plate).all()
    if request.method=="POST":
        q.vehicle_id=int(request.form["vehicle_id"])
        q.valid_until=datetime.fromisoformat(request.form["valid_until"]).date() if request.form.get("valid_until") else None
        q.notes=request.form.get("notes")
        q.vat=float(request.form.get("vat") or VAT_DEFAULT)
        q.discount=float(request.form.get("discount") or 0)
        # If converted, return old stock before replacing items.
        if q.stock_applied:
            apply_stock(q.items, reverse=True)
            q.stock_applied=False
        q.items.clear()
        descs=request.form.getlist("item_description[]"); refs=request.form.getlist("item_reference[]")
        types=request.form.getlist("item_type[]"); qtys=request.form.getlist("item_quantity[]"); prices=request.form.getlist("item_price[]")
        for d,r,t,qty,p in zip(descs,refs,types,qtys,prices):
            if d.strip():
                q.items.append(QuoteItem(item_type=t or "Peça", description=d.strip(), reference=r,
                    quantity=float(qty or 1), unit_price=float(p or 0), vat=q.vat))
        db.session.commit()
        flash("Orçamento alterado.")
        return redirect(url_for("quote_detail",id=id))
    return render_template("quote_form.html", vehicles=vehicles, parts=Part.query.filter_by(active=True).order_by(Part.description).all(),
                           services=Service.query.filter_by(active=True).order_by(Service.name).all(), q=q, edit_mode=True)

@app.route("/quotes/<int:id>/print")
def quote_print(id):
    q=Quote.query.get_or_404(id)
    return render_template("quote_print.html", q=q, totals=totals(q.items,q.discount,q.vat))

@app.route("/api/catalog")
def catalog_api():
    q = request.args.get("q", "").strip()
    parts = Part.query.filter_by(active=True)
    services = Service.query.filter_by(active=True)
    if q:
        like = f"%{q}%"
        parts = parts.filter(or_(Part.code.ilike(like), Part.description.ilike(like), Part.supplier.ilike(like)))
        services = services.filter(or_(Service.code.ilike(like), Service.name.ilike(like), Service.description.ilike(like)))
    data = []
    for p in parts.order_by(Part.description).limit(30).all():
        data.append({"id": p.id, "type": "Peça", "code": p.code, "description": p.description,
                     "price": p.sale_price or 0, "vat": p.vat or VAT_DEFAULT, "stock": p.quantity or 0})
    for s in services.order_by(Service.name).limit(30).all():
        data.append({"id": s.id, "type": "Mão de obra", "code": s.code, "description": s.name,
                     "price": s.sale_price or 0, "vat": s.vat or VAT_DEFAULT, "stock": None})
    return jsonify(data)

@app.route("/stock")
def stock():
    q=request.args.get("q","").strip()
    query=Part.query
    if q: query=query.filter(or_(Part.code.ilike(f"%{q}%"),Part.description.ilike(f"%{q}%"),Part.supplier.ilike(f"%{q}%")))
    return render_template("stock.html", parts=query.order_by(Part.description).all(),q=q)

@app.route("/stock/new", methods=["GET","POST"])
def new_part():
    if request.method=="POST":
        p=Part(code=request.form["code"].strip(),description=request.form["description"].strip(),supplier=request.form.get("supplier"),
               purchase_price=float(request.form.get("purchase_price") or 0),sale_price=float(request.form.get("sale_price") or 0),
               quantity=int(request.form.get("quantity") or 0),minimum_stock=int(request.form.get("minimum_stock") or 0),
               vat=float(request.form.get("vat") or VAT_DEFAULT))
        db.session.add(p); db.session.commit(); flash("Peça criada."); return redirect(url_for("stock"))
    return render_template("part_form.html")

@app.route("/stock/<int:id>/edit", methods=["GET","POST"])
def edit_part(id):
    p=Part.query.get_or_404(id)
    if request.method=="POST":
        p.code=request.form["code"].strip()
        p.description=request.form["description"].strip()
        p.supplier=request.form.get("supplier")
        p.purchase_price=float(request.form.get("purchase_price") or 0)
        p.sale_price=float(request.form.get("sale_price") or 0)
        p.quantity=int(float(request.form.get("quantity") or 0))
        p.minimum_stock=int(float(request.form.get("minimum_stock") or 0))
        p.vat=float(request.form.get("vat") or VAT_DEFAULT)
        p.active=bool(request.form.get("active"))
        db.session.commit(); flash("Peça alterada.")
        return redirect(url_for("stock"))
    return render_template("part_form.html", p=p, edit_mode=True)

@app.route("/services")
def services():
    return render_template("services.html", services=Service.query.order_by(Service.name).all())

@app.route("/services/new", methods=["GET","POST"])
def new_service():
    if request.method=="POST":
        s=Service(code=request.form["code"].strip(),name=request.form["name"].strip(),description=request.form.get("description"),
                  cost_price=float(request.form.get("cost_price") or 0),sale_price=float(request.form.get("sale_price") or 0),
                  vat=float(request.form.get("vat") or VAT_DEFAULT))
        db.session.add(s); db.session.commit(); flash("Serviço criado."); return redirect(url_for("services"))
    return render_template("service_form.html")

@app.route("/agenda")
def agenda():
    return render_template("agenda.html", appointments=Appointment.query.order_by(Appointment.start_at).all())

@app.route("/agenda/new", methods=["GET","POST"])
def new_appointment():
    if request.method=="POST":
        dt=datetime.fromisoformat(request.form["start_at"])
        end=datetime.fromisoformat(request.form["end_at"]) if request.form.get("end_at") else None
        a=Appointment(start_at=dt,end_at=end,client_name=request.form["client_name"],plate=request.form.get("plate"),
                      service=request.form.get("service"),mechanic=request.form.get("mechanic"),status=request.form.get("status","Marcada"))
        db.session.add(a); db.session.commit(); flash("Marcação criada."); return redirect(url_for("agenda"))
    return render_template("appointment_form.html")


@app.route("/invoices")
def invoices():
    return render_template("invoices.html", invoices=Invoice.query.order_by(Invoice.id.desc()).all())

@app.route("/invoices/new", methods=["GET","POST"])
def new_invoice():
    clients=Client.query.order_by(Client.name).all()
    vehicles=Vehicle.query.order_by(Vehicle.plate).all()
    if request.method=="POST":
        inv=Invoice(number=next_number("FT",Invoice), client_id=int(request.form["client_id"]),
                    vehicle_id=int(request.form["vehicle_id"]) if request.form.get("vehicle_id") else None,
                    notes=request.form.get("notes"), vat=float(request.form.get("vat") or VAT_DEFAULT),
                    discount=float(request.form.get("discount") or 0))
        db.session.add(inv); db.session.flush()
        descs=request.form.getlist("item_description[]"); refs=request.form.getlist("item_reference[]")
        types=request.form.getlist("item_type[]"); qtys=request.form.getlist("item_quantity[]"); prices=request.form.getlist("item_price[]")
        for d,r,t,qty,p in zip(descs,refs,types,qtys,prices):
            if d.strip():
                inv.items.append(InvoiceItem(item_type=t or "Peça",description=d.strip(),reference=r,
                    quantity=float(qty or 1),unit_price=float(p or 0),vat=inv.vat))
        try:
            apply_stock(inv.items); inv.stock_applied=True
            db.session.commit(); flash(f"Fatura {inv.number} criada.")
            return redirect(url_for("invoice_detail",id=inv.id))
        except ValueError as e:
            db.session.rollback(); flash(str(e))
    return render_template("invoice_form.html",clients=clients,vehicles=vehicles,
                           parts=Part.query.filter_by(active=True).order_by(Part.description).all(),
                           services=Service.query.filter_by(active=True).order_by(Service.name).all())

@app.route("/invoices/<int:id>")
def invoice_detail(id):
    inv=Invoice.query.get_or_404(id)
    return render_template("invoice_detail.html", inv=inv, totals=totals(inv.items,inv.discount,inv.vat))

@app.route("/invoices/<int:id>/print")
def invoice_print(id):
    inv=Invoice.query.get_or_404(id)
    return render_template("invoice_print.html", inv=inv, totals=totals(inv.items,inv.discount,inv.vat))

@app.route("/settings", methods=["GET","POST"])
def settings():
    s=Setting.query.first()
    if not s:
        s=Setting(); db.session.add(s); db.session.commit()
    if request.method=="POST":
        s.company_name=request.form.get("company_name","JF Auto Mecânica"); s.nif=request.form.get("nif","")
        s.phone=request.form.get("phone",""); s.email=request.form.get("email",""); s.address=request.form.get("address","")
        s.vat=float(request.form.get("vat") or VAT_DEFAULT); db.session.commit(); flash("Definições guardadas.")
        return redirect(url_for("settings"))
    return render_template("settings.html",s=s)

def migrate_sqlite_schema():
    """Garante que a base SQLite tem todas as tabelas/colunas desta versão."""
    db.create_all()
    if db.engine.url.get_backend_name() != "sqlite":
        return
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    existing_tables = set(insp.get_table_names())

    # Tabelas novas: create_all já as criou. Para tabelas antigas,
    # acrescentamos apenas colunas que não existam.
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        cols = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in cols:
                continue
            typ = col.type.compile(db.engine.dialect)
            sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {typ}'
            if not col.nullable:
                if any(x in typ.upper() for x in ("INT","REAL","NUMERIC","FLOAT","DECIMAL")):
                    sql += " NOT NULL DEFAULT 0"
                else:
                    sql += " NOT NULL DEFAULT ''"
            with db.engine.begin() as conn:
                conn.execute(text(sql))

with app.app_context():
    migrate_sqlite_schema()
    if not Setting.query.first():
        db.session.add(Setting())
        db.session.commit()
    if not User.query.first():
        default_user = os.getenv("ADMIN_USERNAME", "admin")
        default_password = os.getenv("ADMIN_PASSWORD", "JFauto2026!")
        db.session.add(User(username=default_user, password_hash=generate_password_hash(default_password)))
        db.session.commit()
    backup_database()

@app.get("/health")
def health():
    return {"status": "ok"}, 200

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
