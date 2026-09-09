from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import or_, func, inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os, shutil, traceback, uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'oficina-pro-chave-alterar')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, 'oficina.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f"sqlite:///{DB_FILE.replace(os.sep, '/')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
VAT_DEFAULT = 23.0

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)

class Client(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(150),nullable=False); nif=db.Column(db.String(30)); phone=db.Column(db.String(40)); email=db.Column(db.String(120)); address=db.Column(db.String(250)); notes=db.Column(db.Text)
    vehicles=db.relationship('Vehicle',backref='client',cascade='all, delete-orphan')
class Vehicle(db.Model):
    id=db.Column(db.Integer,primary_key=True); plate=db.Column(db.String(20),nullable=False,index=True); brand=db.Column(db.String(80)); model=db.Column(db.String(80)); year=db.Column(db.Integer); vin=db.Column(db.String(80)); km=db.Column(db.Integer,default=0); fuel=db.Column(db.String(30)); client_id=db.Column(db.Integer,db.ForeignKey('client.id'),nullable=False)
    work_orders=db.relationship('WorkOrder',backref='vehicle',cascade='all, delete-orphan')
class Part(db.Model):
    id=db.Column(db.Integer,primary_key=True); code=db.Column(db.String(60),unique=True,nullable=False); description=db.Column(db.String(160),nullable=False); supplier=db.Column(db.String(120)); purchase_price=db.Column(db.Float,default=0); sale_price=db.Column(db.Float,default=0); quantity=db.Column(db.Integer,default=0); minimum_stock=db.Column(db.Integer,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT); active=db.Column(db.Boolean,default=True)
class Service(db.Model):
    id=db.Column(db.Integer,primary_key=True); code=db.Column(db.String(60),unique=True,nullable=False); name=db.Column(db.String(160),nullable=False); description=db.Column(db.String(250)); sale_price=db.Column(db.Float,default=0); cost_price=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT); active=db.Column(db.Boolean,default=True)
class WorkOrder(db.Model):
    id=db.Column(db.Integer,primary_key=True); number=db.Column(db.String(30),unique=True,nullable=False); status=db.Column(db.String(40),default='Aberta'); complaint=db.Column(db.Text); diagnosis=db.Column(db.Text); work_done=db.Column(db.Text); mechanic=db.Column(db.String(120)); entry_at=db.Column(db.DateTime,default=datetime.utcnow); exit_at=db.Column(db.DateTime); km=db.Column(db.Integer,default=0); discount=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT); vehicle_id=db.Column(db.Integer,db.ForeignKey('vehicle.id'),nullable=False); stock_applied=db.Column(db.Boolean,default=False)
    items=db.relationship('WorkItem',backref='order',cascade='all, delete-orphan')
class WorkItem(db.Model):
    id=db.Column(db.Integer,primary_key=True); order_id=db.Column(db.Integer,db.ForeignKey('work_order.id'),nullable=False); item_type=db.Column(db.String(20),default='Peça'); description=db.Column(db.String(250),nullable=False); reference=db.Column(db.String(80)); quantity=db.Column(db.Float,default=1); unit_price=db.Column(db.Float,default=0); discount=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT)
class Appointment(db.Model):
    id=db.Column(db.Integer,primary_key=True); start_at=db.Column(db.DateTime,nullable=False); end_at=db.Column(db.DateTime); client_name=db.Column(db.String(150),nullable=False); plate=db.Column(db.String(20)); service=db.Column(db.String(200)); mechanic=db.Column(db.String(120)); status=db.Column(db.String(40),default='Marcada')
class Quote(db.Model):
    id=db.Column(db.Integer,primary_key=True); number=db.Column(db.String(30),unique=True,nullable=False); status=db.Column(db.String(30),default='Pendente'); created_at=db.Column(db.DateTime,default=datetime.utcnow); valid_until=db.Column(db.Date); notes=db.Column(db.Text); discount=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT); vehicle_id=db.Column(db.Integer,db.ForeignKey('vehicle.id'),nullable=False); stock_applied=db.Column(db.Boolean,default=False)
    vehicle=db.relationship('Vehicle'); items=db.relationship('QuoteItem',backref='quote',cascade='all, delete-orphan')
class QuoteItem(db.Model):
    id=db.Column(db.Integer,primary_key=True); quote_id=db.Column(db.Integer,db.ForeignKey('quote.id'),nullable=False); item_type=db.Column(db.String(20),default='Peça'); description=db.Column(db.String(250),nullable=False); reference=db.Column(db.String(80)); quantity=db.Column(db.Float,default=1); unit_price=db.Column(db.Float,default=0); discount=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT)
class Invoice(db.Model):
    id=db.Column(db.Integer,primary_key=True); client_id=db.Column(db.Integer,db.ForeignKey('client.id'),nullable=True); number=db.Column(db.String(30),unique=True,nullable=False); status=db.Column(db.String(30),default='Emitida'); payment_status=db.Column(db.String(30),default='Por pagar'); due_date=db.Column(db.Date); created_at=db.Column(db.DateTime,default=datetime.utcnow); client_name=db.Column(db.String(150)); nif=db.Column(db.String(30)); phone=db.Column(db.String(40)); address=db.Column(db.String(250)); vehicle_info=db.Column(db.String(160)); notes=db.Column(db.Text); discount=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT)
    client=db.relationship('Client',backref='invoices')
    items=db.relationship('InvoiceItem',backref='invoice',cascade='all, delete-orphan')
class InvoiceItem(db.Model):
    id=db.Column(db.Integer,primary_key=True); invoice_id=db.Column(db.Integer,db.ForeignKey('invoice.id'),nullable=False); item_type=db.Column(db.String(20),default='Peça'); description=db.Column(db.String(250),nullable=False); reference=db.Column(db.String(80)); quantity=db.Column(db.Float,default=1); unit_price=db.Column(db.Float,default=0); discount=db.Column(db.Float,default=0); vat=db.Column(db.Float,default=VAT_DEFAULT)
class Receipt(db.Model):
    id=db.Column(db.String(36),primary_key=True,default=lambda:str(uuid.uuid4())); number=db.Column(db.String(30),unique=True,nullable=False); created_at=db.Column(db.DateTime,default=datetime.utcnow); invoice_id=db.Column(db.Integer,db.ForeignKey('invoice.id')); client_name=db.Column(db.String(150)); amount=db.Column(db.Float,default=0); payment_method=db.Column(db.String(50),default='Transferência'); notes=db.Column(db.Text)
    invoice=db.relationship('Invoice',backref=db.backref('receipts',cascade='all, delete-orphan'))
class CreditNote(db.Model):
    id=db.Column(db.String(36),primary_key=True,default=lambda:str(uuid.uuid4())); number=db.Column(db.String(30),unique=True,nullable=False); created_at=db.Column(db.DateTime,default=datetime.utcnow); invoice_id=db.Column(db.Integer,db.ForeignKey('invoice.id')); client_name=db.Column(db.String(150)); amount=db.Column(db.Float,default=0); reason=db.Column(db.String(250)); notes=db.Column(db.Text)
    invoice=db.relationship('Invoice',backref=db.backref('credit_notes',cascade='all, delete-orphan'))
class Setting(db.Model):
    id=db.Column(db.Integer,primary_key=True); company_name=db.Column(db.String(150),default='JF Auto Mecânica'); nif=db.Column(db.String(30),default=''); phone=db.Column(db.String(40),default=''); email=db.Column(db.String(120),default=''); address=db.Column(db.String(250),default=''); vat=db.Column(db.Float,default=VAT_DEFAULT)

def item_net(i): return max(0,(i.quantity or 0)*(i.unit_price or 0)-(i.discount or 0))
def totals(items,discount=0,vat=VAT_DEFAULT):
    subtotal=sum(item_net(i) for i in items); disc=max(0,discount or 0); taxable=max(0,subtotal-disc); iva=taxable*(vat or 0)/100; return subtotal,disc,iva,taxable+iva
@app.template_filter('eur')
def eur(v): return f'{(v or 0):,.2f} €'.replace(',','X').replace('.',',').replace('X','.')
@app.context_processor
def globals(): return {'now':datetime.now(),'settings':Setting.query.first(),'item_net':item_net,'totals':totals,'invoice_total':invoice_total,'invoice_received':invoice_received,'invoice_credits':invoice_credits,'invoice_balance':invoice_balance,'current_user':User.query.get(session.get('user_id')) if session.get('user_id') else None}

def login_required(fn):
    @wraps(fn)
    def wrapper(*a,**kw):
        if not session.get('user_id'): return redirect(url_for('login',next=request.path))
        return fn(*a,**kw)
    return wrapper
@app.route('/health')
def health():
    return 'OK', 200

@app.before_request
def auth_gate():
    if request.endpoint in {'login','static','health'}: return
    if not session.get('user_id'): return redirect(url_for('login',next=request.path))

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    try:
        with open(os.path.join(BASE_DIR,'erro.log'),'a',encoding='utf-8') as f: f.write('\n\n'+'='*80+'\n'+datetime.now().isoformat()+'\n'+request.method+' '+request.path+'\n'+traceback.format_exc())
    except Exception: pass
    db.session.rollback(); return render_template('error.html',error=str(error)),500

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form.get('username','').strip()).first()
        if u and u.active and check_password_hash(u.password_hash,request.form.get('password','')):
            session.clear(); session['user_id']=u.id; return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Utilizador ou palavra-passe incorretos.','danger')
    return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

def _dashboard_data():
    today=date.today()
    open_orders=WorkOrder.query.filter(WorkOrder.status!='Entregue').count()
    low_stock=Part.query.filter(Part.quantity<=Part.minimum_stock,Part.active==True).count()
    month_start=datetime(today.year,today.month,1)
    month_orders=WorkOrder.query.filter(WorkOrder.entry_at>=month_start).all()
    revenue=sum(totals(o.items,o.discount,o.vat)[3] for o in month_orders)
    quotes_pending=Quote.query.filter_by(status='Pendente').count()
    appointments=Appointment.query.filter(Appointment.start_at>=datetime.now()).order_by(Appointment.start_at).limit(8).all()
    active_orders=WorkOrder.query.filter(WorkOrder.status!='Entregue').order_by(WorkOrder.entry_at.desc()).limit(8).all()
    pending_quotes=Quote.query.filter_by(status='Pendente').order_by(Quote.created_at.desc()).limit(8).all()
    return dict(clients=Client.query.count(),vehicles=Vehicle.query.count(),open_orders=open_orders,low_stock=low_stock,revenue=revenue,quotes_pending=quotes_pending,appointments=appointments,active_orders=active_orders,pending_quotes=pending_quotes)

@app.route('/')
@login_required
def dashboard():
    return render_template('welcome.html', **_dashboard_data())

@app.route('/workboard')
@login_required
def workboard():
    return render_template('workboard.html', **_dashboard_data())

@app.route('/clients')
def clients():
    q=request.args.get('q','').strip(); query=Client.query
    if q: query=query.filter(or_(Client.name.ilike(f'%{q}%'),Client.nif.ilike(f'%{q}%'),Client.phone.ilike(f'%{q}%')))
    return render_template('clients.html',clients=query.order_by(Client.name).all(),q=q)
@app.route('/clients/new',methods=['GET','POST'])
def new_client():
    if request.method=='POST':
        c=Client(name=request.form['name'].strip(),nif=request.form.get('nif'),phone=request.form.get('phone'),email=request.form.get('email'),address=request.form.get('address'),notes=request.form.get('notes')); db.session.add(c); db.session.commit(); flash('Cliente criado.'); return redirect(url_for('clients'))
    return render_template('client_form.html')
@app.route('/clients/<int:id>/edit',methods=['GET','POST'])
def edit_client(id):
    c=Client.query.get_or_404(id)
    if request.method=='POST':
        for x in ['name','nif','phone','email','address','notes']:
            setattr(c,x,request.form.get(x))
        db.session.commit(); flash('Cliente atualizado.'); return redirect(url_for('clients'))
    return render_template('client_form.html',c=c)

@app.route('/vehicles')
def vehicles():
    q=request.args.get('q','').strip(); query=Vehicle.query
    if q: query=query.filter(or_(Vehicle.plate.ilike(f'%{q}%'),Vehicle.brand.ilike(f'%{q}%'),Vehicle.model.ilike(f'%{q}%')))
    return render_template('vehicles.html',vehicles=query.order_by(Vehicle.plate).all(),q=q)
@app.route('/vehicles/new',methods=['GET','POST'])
def new_vehicle():
    clients=Client.query.order_by(Client.name).all()
    if request.method=='POST':
        v=Vehicle(plate=request.form['plate'].upper().strip(),brand=request.form.get('brand'),model=request.form.get('model'),year=int(request.form['year']) if request.form.get('year') else None,vin=request.form.get('vin'),km=int(request.form.get('km') or 0),fuel=request.form.get('fuel'),client_id=int(request.form['client_id'])); db.session.add(v); db.session.commit(); flash('Viatura criada.'); return redirect(url_for('vehicles'))
    return render_template('vehicle_form.html',clients=clients)
@app.route('/vehicles/<int:id>/edit',methods=['GET','POST'])
def edit_vehicle(id):
    v=Vehicle.query.get_or_404(id); clients=Client.query.order_by(Client.name).all()
    if request.method=='POST':
        v.plate=request.form['plate'].upper().strip(); v.brand=request.form.get('brand'); v.model=request.form.get('model'); v.year=int(request.form['year']) if request.form.get('year') else None; v.vin=request.form.get('vin'); v.km=int(request.form.get('km') or 0); v.fuel=request.form.get('fuel'); v.client_id=int(request.form['client_id']); db.session.commit(); flash('Viatura atualizada.'); return redirect(url_for('vehicles'))
    return render_template('vehicle_form.html',v=v,clients=clients)

def next_number(prefix,model):
    y=datetime.now().year; count=model.query.filter(model.number.like(f'{prefix}-{y}-%')).count()+1; return f'{prefix}-{y}-{count:05d}'
def add_posted_items(parent,prefix,item_cls):
    descs=request.form.getlist(f'{prefix}_description[]'); refs=request.form.getlist(f'{prefix}_reference[]'); types=request.form.getlist(f'{prefix}_type[]'); qtys=request.form.getlist(f'{prefix}_quantity[]'); prices=request.form.getlist(f'{prefix}_price[]'); vats=request.form.getlist(f'{prefix}_vat[]')
    for d,r,t,q,p,v in zip(descs,refs,types,qtys,prices,vats):
        if d.strip(): parent.items.append(item_cls(description=d.strip(),reference=r,item_type=t or 'Peça',quantity=float(q or 1),unit_price=float(p or 0),vat=float(v or VAT_DEFAULT)))

@app.route('/orders')
def orders():
    status=request.args.get('status',''); q=request.args.get('q','').strip(); query=WorkOrder.query
    if status: query=query.filter_by(status=status)
    if q: query=query.join(Vehicle).filter(or_(WorkOrder.number.ilike(f'%{q}%'),Vehicle.plate.ilike(f'%{q}%')))
    return render_template('orders.html',orders=query.order_by(WorkOrder.id.desc()).all(),q=q,status=status)
@app.route('/orders/new',methods=['GET','POST'])
def new_order():
    vehicles=Vehicle.query.order_by(Vehicle.plate).all(); parts=Part.query.filter_by(active=True).order_by(Part.description).all(); services=Service.query.filter_by(active=True).order_by(Service.name).all()
    if request.method=='POST':
        n=next_number('OR',WorkOrder); o=WorkOrder(number=n,vehicle_id=int(request.form['vehicle_id']),complaint=request.form.get('complaint'),mechanic=request.form.get('mechanic'),km=int(request.form.get('km') or 0),vat=float(request.form.get('vat') or VAT_DEFAULT),discount=float(request.form.get('discount') or 0)); db.session.add(o); db.session.flush(); add_posted_items(o,'item',WorkItem); db.session.commit(); flash(f'Ordem {n} criada.'); return redirect(url_for('order_detail',id=o.id))
    return render_template('order_form.html',vehicles=vehicles,parts=parts,services=services)
@app.route('/orders/<int:id>')
def order_detail(id):
    o=WorkOrder.query.get_or_404(id); return render_template('order_detail.html',o=o,totals=totals(o.items,o.discount,o.vat))
@app.route('/orders/<int:id>/update',methods=['POST'])
def order_update(id):
    o=WorkOrder.query.get_or_404(id); o.status=request.form.get('status',o.status); o.mechanic=request.form.get('mechanic'); o.diagnosis=request.form.get('diagnosis'); o.work_done=request.form.get('work_done'); o.discount=float(request.form.get('discount') or 0); o.vat=float(request.form.get('vat') or VAT_DEFAULT); o.km=int(request.form.get('km') or o.km or 0)
    if o.status=='Entregue' and not o.exit_at: o.exit_at=datetime.utcnow()
    if o.status=='Entregue' and not o.stock_applied:
        ok,msg=apply_stock(o.items)
        if not ok: flash(msg,'danger'); return redirect(url_for('order_detail',id=id))
        o.stock_applied=True
    db.session.commit(); flash('Ordem atualizada.'); return redirect(url_for('order_detail',id=id))
@app.route('/orders/<int:id>/item',methods=['POST'])
def order_item(id):
    o=WorkOrder.query.get_or_404(id); o.items.append(WorkItem(item_type=request.form.get('item_type','Peça'),description=request.form['description'],reference=request.form.get('reference'),quantity=float(request.form.get('quantity') or 1),unit_price=float(request.form.get('unit_price') or 0),vat=float(request.form.get('vat') or o.vat))); db.session.commit(); return redirect(url_for('order_detail',id=id))
@app.route('/orders/<int:id>/item/<int:item_id>/edit',methods=['GET','POST'])
def order_item_edit(id,item_id):
    i=WorkItem.query.filter_by(id=item_id,order_id=id).first_or_404()
    if request.method=='POST': i.item_type=request.form.get('item_type','Peça'); i.description=request.form['description']; i.reference=request.form.get('reference'); i.quantity=float(request.form.get('quantity') or 1); i.unit_price=float(request.form.get('unit_price') or 0); i.vat=float(request.form.get('vat') or 23); db.session.commit(); flash('Item da ordem atualizado.'); return redirect(url_for('order_detail',id=id))
    return render_template('item_edit.html',i=i,title='Editar item da ordem',back=url_for('order_detail',id=id))
@app.route('/orders/<int:id>/item/<int:item_id>/delete',methods=['POST'])
def order_item_delete(id,item_id):
    i=WorkItem.query.filter_by(id=item_id,order_id=id).first_or_404(); db.session.delete(i); db.session.commit(); return redirect(url_for('order_detail',id=id))
@app.route('/orders/<int:id>/print')
def order_print(id): return render_template('order_print.html',o=WorkOrder.query.get_or_404(id),totals=totals(WorkOrder.query.get_or_404(id).items,WorkOrder.query.get_or_404(id).discount,WorkOrder.query.get_or_404(id).vat))

@app.route('/quotes')
def quotes():
    q=request.args.get('q','').strip(); query=Quote.query.join(Vehicle).join(Client)
    if q: query=query.filter(or_(Quote.number.ilike(f'%{q}%'),Vehicle.plate.ilike(f'%{q}%'),Client.name.ilike(f'%{q}%')))
    return render_template('quotes.html',quotes=query.order_by(Quote.id.desc()).all(),q=q)
@app.route('/quotes/new',methods=['GET','POST'])
def new_quote():
    vehicles=Vehicle.query.order_by(Vehicle.plate).all()
    if request.method=='POST':
        q=Quote(number=next_number('OC',Quote),vehicle_id=int(request.form['vehicle_id']),valid_until=datetime.fromisoformat(request.form['valid_until']).date() if request.form.get('valid_until') else None,notes=request.form.get('notes'),vat=float(request.form.get('vat') or VAT_DEFAULT),discount=float(request.form.get('discount') or 0)); db.session.add(q); db.session.flush(); add_posted_items(q,'item',QuoteItem); db.session.commit(); flash(f'Orçamento {q.number} criado.'); return redirect(url_for('quote_detail',id=q.id))
    return render_template('quote_form.html',vehicles=vehicles)
@app.route('/quotes/<int:id>')
def quote_detail(id):
    q=Quote.query.get_or_404(id); return render_template('quote_detail.html',q=q,totals=totals(q.items,q.discount,q.vat))
@app.route('/quotes/<int:id>/edit',methods=['GET','POST'])
def quote_edit(id):
    q=Quote.query.get_or_404(id)
    if q.status=='Convertido': flash('Um orçamento convertido não pode ser alterado.','danger'); return redirect(url_for('quote_detail',id=id))
    if request.method=='POST':
        q.vehicle_id=int(request.form['vehicle_id']); q.valid_until=datetime.fromisoformat(request.form['valid_until']).date() if request.form.get('valid_until') else None; q.notes=request.form.get('notes'); q.discount=float(request.form.get('discount') or 0); q.vat=float(request.form.get('vat') or 23)
        for i in list(q.items): db.session.delete(i)
        db.session.flush(); add_posted_items(q,'item',QuoteItem); db.session.commit(); flash('Orçamento atualizado.'); return redirect(url_for('quote_detail',id=id))
    return render_template('quote_form.html',q=q,vehicles=Vehicle.query.order_by(Vehicle.plate).all(),edit=True)
@app.route('/quotes/<int:id>/status',methods=['POST'])
def quote_status(id):
    q=Quote.query.get_or_404(id); new=request.form['status']
    if new=='Convertido' and not q.stock_applied:
        ok,msg=apply_stock(q.items)
        if not ok: flash(msg,'danger'); return redirect(url_for('quote_detail',id=id))
        q.stock_applied=True
    q.status=new; db.session.commit(); flash('Estado do orçamento atualizado.'); return redirect(url_for('quote_detail',id=id))
@app.route('/quotes/<int:id>/print')
def quote_print(id):
    q=Quote.query.get_or_404(id); return render_template('quote_print.html',q=q,totals=totals(q.items,q.discount,q.vat))

def find_part(item):
    if item.reference:
        p=Part.query.filter_by(code=item.reference.strip()).first()
        if p: return p
    return Part.query.filter(func.lower(Part.description)==func.lower(item.description.strip())).first()
def apply_stock(items):
    needs=[]
    for i in items:
        if (i.item_type or '').lower()=='peça':
            p=find_part(i)
            if p:
                qty=int(round(i.quantity or 0)); needs.append((p,qty))
    for p,qty in needs:
        if qty>p.quantity: return False,f'Stock insuficiente para {p.description}: disponível {p.quantity}, necessário {qty}.'
    for p,qty in needs: p.quantity-=qty
    return True,''

@app.route('/api/catalog')
def catalog_api():
    q=request.args.get('q','').strip(); parts=Part.query.filter_by(active=True); services=Service.query.filter_by(active=True)
    if q:
        like=f'%{q}%'; parts=parts.filter(or_(Part.code.ilike(like),Part.description.ilike(like),Part.supplier.ilike(like))); services=services.filter(or_(Service.code.ilike(like),Service.name.ilike(like),Service.description.ilike(like)))
    data=[]
    for p in parts.order_by(Part.description).limit(30).all(): data.append({'id':p.id,'type':'Peça','code':p.code,'description':p.description,'price':p.sale_price or 0,'vat':p.vat or VAT_DEFAULT,'stock':p.quantity or 0})
    for s in services.order_by(Service.name).limit(30).all(): data.append({'id':s.id,'type':'Mão de obra','code':s.code,'description':s.name,'price':s.sale_price or 0,'vat':s.vat or VAT_DEFAULT,'stock':None})
    return jsonify(data)

@app.route('/stock')
def stock():
    q=request.args.get('q','').strip(); query=Part.query
    if q: query=query.filter(or_(Part.code.ilike(f'%{q}%'),Part.description.ilike(f'%{q}%'),Part.supplier.ilike(f'%{q}%')))
    return render_template('stock.html',parts=query.order_by(Part.description).all(),q=q)
@app.route('/stock/new',methods=['GET','POST'])
def new_part():
    if request.method=='POST':
        p=Part(code=request.form['code'].strip(),description=request.form['description'].strip(),supplier=request.form.get('supplier'),purchase_price=float(request.form.get('purchase_price') or 0),sale_price=float(request.form.get('sale_price') or 0),quantity=int(request.form.get('quantity') or 0),minimum_stock=int(request.form.get('minimum_stock') or 0),vat=float(request.form.get('vat') or 23)); db.session.add(p); db.session.commit(); flash('Peça criada.'); return redirect(url_for('stock'))
    return render_template('part_form.html')
@app.route('/stock/<int:id>/edit',methods=['GET','POST'])
def edit_part(id):
    p=Part.query.get_or_404(id)
    if request.method=='POST':
        p.code=request.form['code'].strip(); p.description=request.form['description'].strip(); p.supplier=request.form.get('supplier'); p.purchase_price=float(request.form.get('purchase_price') or 0); p.sale_price=float(request.form.get('sale_price') or 0); p.quantity=int(request.form.get('quantity') or 0); p.minimum_stock=int(request.form.get('minimum_stock') or 0); p.vat=float(request.form.get('vat') or 23); db.session.commit(); flash('Stock atualizado.'); return redirect(url_for('stock'))
    return render_template('part_form.html',p=p,edit=True)

@app.route('/services')
def services(): return render_template('services.html',services=Service.query.order_by(Service.name).all())
@app.route('/services/new',methods=['GET','POST'])
def new_service():
    if request.method=='POST':
        s=Service(code=request.form['code'].strip(),name=request.form['name'].strip(),description=request.form.get('description'),cost_price=float(request.form.get('cost_price') or 0),sale_price=float(request.form.get('sale_price') or 0),vat=float(request.form.get('vat') or 23)); db.session.add(s); db.session.commit(); flash('Serviço criado.'); return redirect(url_for('services'))
    return render_template('service_form.html')
@app.route('/services/<int:id>/edit',methods=['GET','POST'])
def edit_service(id):
    s=Service.query.get_or_404(id)
    if request.method=='POST':
        s.code=request.form['code'].strip(); s.name=request.form['name'].strip(); s.description=request.form.get('description'); s.cost_price=float(request.form.get('cost_price') or 0); s.sale_price=float(request.form.get('sale_price') or 0); s.vat=float(request.form.get('vat') or 23); db.session.commit(); flash('Serviço atualizado.'); return redirect(url_for('services'))
    return render_template('service_form.html',s=s,edit=True)

@app.route('/agenda')
def agenda(): return render_template('agenda.html',appointments=Appointment.query.order_by(Appointment.start_at).all())
@app.route('/agenda/new',methods=['GET','POST'])
def new_appointment():
    if request.method=='POST':
        start=datetime.fromisoformat(request.form['start_at']); end=datetime.fromisoformat(request.form['end_at']) if request.form.get('end_at') else None
        a=Appointment(start_at=start,end_at=end,client_name=request.form['client_name'],plate=request.form.get('plate'),service=request.form.get('service'),mechanic=request.form.get('mechanic'),status=request.form.get('status','Marcada')); db.session.add(a); db.session.commit(); flash('Marcação criada.'); return redirect(url_for('agenda'))
    return render_template('appointment_form.html')
@app.route('/agenda/<int:id>/edit',methods=['GET','POST'])
def edit_appointment(id):
    a=Appointment.query.get_or_404(id)
    if request.method=='POST':
        a.start_at=datetime.fromisoformat(request.form['start_at']); a.end_at=datetime.fromisoformat(request.form['end_at']) if request.form.get('end_at') else None; a.client_name=request.form['client_name']; a.plate=request.form.get('plate'); a.service=request.form.get('service'); a.mechanic=request.form.get('mechanic'); a.status=request.form.get('status'); db.session.commit(); flash('Marcação atualizada.'); return redirect(url_for('agenda'))
    return render_template('appointment_form.html',a=a,edit=True)

def invoice_total(inv): return totals(inv.items,inv.discount,inv.vat)[3]
def invoice_received(inv): return sum((r.amount or 0) for r in inv.receipts)
def invoice_credits(inv): return sum((c.amount or 0) for c in inv.credit_notes)
def invoice_balance(inv): return max(0, invoice_total(inv)-invoice_received(inv)-invoice_credits(inv))
def refresh_invoice_status(inv):
    total=invoice_total(inv); received=invoice_received(inv); balance=invoice_balance(inv)
    if balance <= 0.009: inv.payment_status='Pago'
    elif received > 0: inv.payment_status='Parcial'
    else: inv.payment_status='Por pagar'

@app.route('/invoices')
def invoices():
    invs=Invoice.query.order_by(Invoice.created_at.desc()).all()
    for i in invs: refresh_invoice_status(i)
    db.session.commit()
    return render_template('invoices.html',invoices=invs)
@app.route('/invoices/new',methods=['GET','POST'])
def new_invoice():
    if request.method=='POST':
        client_id=request.form.get('client_id')
        client=Client.query.get(int(client_id)) if client_id else None
        client_name=(request.form.get('client_name') or '').strip()
        # A tabela invoice existente exige client_id. Se o utilizador escrever um cliente
        # sem selecionar um existente, criamos automaticamente a ficha de cliente.
        if not client:
            if not client_name:
                flash('Indique um cliente para criar a fatura.','danger')
                return render_template('invoice_form.html',clients=Client.query.order_by(Client.name).all())
            client=Client(name=client_name,nif=request.form.get('nif'),phone=request.form.get('phone'),address=request.form.get('address'))
            db.session.add(client); db.session.flush()
        inv=Invoice(client_id=client.id,number=next_number('FT',Invoice),client_name=client.name,nif=request.form.get('nif') or client.nif,phone=request.form.get('phone') or client.phone,address=request.form.get('address') or client.address,vehicle_info=request.form.get('vehicle_info'),notes=request.form.get('notes'),vat=float(request.form.get('vat') or 23),discount=float(request.form.get('discount') or 0),due_date=date.fromisoformat(request.form['due_date']) if request.form.get('due_date') else None)
        db.session.add(inv); db.session.flush(); add_posted_items(inv,'item',InvoiceItem); db.session.commit(); flash(f'Documento {inv.number} criado.'); return redirect(url_for('invoice_detail',id=inv.id))
    return render_template('invoice_form.html',clients=Client.query.order_by(Client.name).all())
@app.route('/invoices/<id>')
def invoice_detail(id):
    inv=Invoice.query.get_or_404(id); refresh_invoice_status(inv); db.session.commit(); return render_template('invoice_detail.html',inv=inv,totals=totals(inv.items,inv.discount,inv.vat),received=invoice_received(inv),credits=invoice_credits(inv),balance=invoice_balance(inv))
@app.route('/invoices/<id>/edit',methods=['GET','POST'])
def invoice_edit(id):
    inv=Invoice.query.get_or_404(id)
    if request.method=='POST':
        client_id=request.form.get('client_id')
        if client_id:
            client=Client.query.get(int(client_id))
            if client: inv.client_id=client.id
        if not inv.client_id:
            client=Client(name=(request.form.get('client_name') or '').strip())
            if not client.name:
                flash('Indique um cliente para a fatura.','danger'); return render_template('invoice_form.html',inv=inv,edit=True,clients=Client.query.order_by(Client.name).all())
            client.nif=request.form.get('nif'); client.phone=request.form.get('phone'); client.address=request.form.get('address'); db.session.add(client); db.session.flush(); inv.client_id=client.id
        inv.client_name=request.form.get('client_name') or inv.client.name; inv.nif=request.form.get('nif') or inv.client.nif; inv.phone=request.form.get('phone') or inv.client.phone; inv.address=request.form.get('address') or inv.client.address; inv.vehicle_info=request.form.get('vehicle_info'); inv.notes=request.form.get('notes'); inv.vat=float(request.form.get('vat') or 23); inv.discount=float(request.form.get('discount') or 0); inv.due_date=date.fromisoformat(request.form['due_date']) if request.form.get('due_date') else None
        for i in list(inv.items): db.session.delete(i)
        db.session.flush(); add_posted_items(inv,'item',InvoiceItem); db.session.commit(); flash('Documento atualizado.'); return redirect(url_for('invoice_detail',id=id))
    return render_template('invoice_form.html',inv=inv,edit=True,clients=Client.query.order_by(Client.name).all())
@app.route('/receipts/new',methods=['GET','POST'])
def new_receipt():
    invs=Invoice.query.order_by(Invoice.created_at.desc()).all()
    if request.method=='POST':
        inv=Invoice.query.get_or_404(request.form.get('invoice_id'))
        amount=float(request.form.get('amount') or 0)
        if amount <= 0 or amount > invoice_balance(inv)+0.01: flash('Valor do recibo inválido.','danger'); return render_template('receipt_form.html',invoices=invs)
        r=Receipt(number=next_number('RC',Receipt),invoice_id=inv.id,client_name=inv.client_name,amount=amount,payment_method=request.form.get('payment_method') or 'Transferência',notes=request.form.get('notes')); db.session.add(r); db.session.flush(); refresh_invoice_status(inv); db.session.commit(); flash(f'Recibo {r.number} criado.'); return redirect(url_for('receipt_detail',id=r.id))
    return render_template('receipt_form.html',invoices=invs)
@app.route('/receipts/<id>')
def receipt_detail(id):
    r=Receipt.query.get_or_404(id); return render_template('receipt_detail.html',receipt=r)
@app.route('/receipts/<id>/print')
def receipt_print(id):
    r=Receipt.query.get_or_404(id); return render_template('receipt_print.html',receipt=r)
@app.route('/credit-notes/new',methods=['GET','POST'])
def new_credit_note():
    invs=Invoice.query.order_by(Invoice.created_at.desc()).all()
    if request.method=='POST':
        inv=Invoice.query.get_or_404(request.form.get('invoice_id')); amount=float(request.form.get('amount') or 0); available=max(0,invoice_total(inv)-invoice_credits(inv))
        if amount <= 0 or amount > available+0.01: flash('Valor da nota de crédito inválido.','danger'); return render_template('credit_note_form.html',invoices=invs)
        c=CreditNote(number=next_number('NC',CreditNote),invoice_id=inv.id,client_name=inv.client_name,amount=amount,reason=request.form.get('reason'),notes=request.form.get('notes')); db.session.add(c); db.session.flush(); refresh_invoice_status(inv); db.session.commit(); flash(f'Nota de crédito {c.number} criada.'); return redirect(url_for('credit_note_detail',id=c.id))
    return render_template('credit_note_form.html',invoices=invs)
@app.route('/credit-notes/<id>')
def credit_note_detail(id):
    c=CreditNote.query.get_or_404(id); return render_template('credit_note_detail.html',credit=c)
@app.route('/credit-notes/<id>/print')
def credit_note_print(id):
    c=CreditNote.query.get_or_404(id); return render_template('credit_note_print.html',credit=c)

@app.route('/receipts')
def receipts(): return render_template('receipts.html',receipts=Receipt.query.order_by(Receipt.created_at.desc()).all())
@app.route('/credit-notes')
def credit_notes(): return render_template('credit_notes.html',credits=CreditNote.query.order_by(CreditNote.created_at.desc()).all())

@app.route('/invoices/<id>/print')
def invoice_print(id):
    inv=Invoice.query.get_or_404(id); return render_template('invoice_print.html',inv=inv,totals=totals(inv.items,inv.discount,inv.vat))

@app.route('/reports')
def reports():
    today=date.today()
    month_start=datetime(today.year,today.month,1)
    month_orders=WorkOrder.query.filter(WorkOrder.entry_at>=month_start,WorkOrder.status=='Entregue').order_by(WorkOrder.entry_at.desc()).all()
    month_invoices=Invoice.query.filter(Invoice.created_at>=month_start).order_by(Invoice.created_at.desc()).all()
    month_total=sum(totals(o.items,o.discount,o.vat)[3] for o in month_orders)+sum(totals(i.items,i.discount,i.vat)[3] for i in month_invoices)
    daily={}
    for o in month_orders:
        d=o.entry_at.date(); daily[d]=daily.get(d,0)+totals(o.items,o.discount,o.vat)[3]
    for i in month_invoices:
        d=i.created_at.date(); daily[d]=daily.get(d,0)+totals(i.items,i.discount,i.vat)[3]
    days=sorted(daily.items(),reverse=True)
    return render_template('reports.html',month_total=month_total,month_orders=month_orders,month_invoices=month_invoices,days=days)

@app.route('/settings',methods=['GET','POST'])
def settings():
    s=Setting.query.first()
    if not s: s=Setting(); db.session.add(s); db.session.commit()
    if request.method=='POST':
        s.company_name=request.form.get('company_name','JF Auto Mecânica'); s.nif=request.form.get('nif',''); s.phone=request.form.get('phone',''); s.email=request.form.get('email',''); s.address=request.form.get('address',''); s.vat=float(request.form.get('vat') or 23); db.session.commit(); flash('Definições guardadas.'); return redirect(url_for('settings'))
    return render_template('settings.html',s=s)
@app.route('/settings/password',methods=['POST'])
def change_password():
    u=User.query.get(session['user_id']); old=request.form.get('old_password',''); new=request.form.get('new_password','')
    if not check_password_hash(u.password_hash,old): flash('Palavra-passe atual incorreta.','danger')
    elif len(new)<8: flash('A nova palavra-passe deve ter pelo menos 8 caracteres.','danger')
    else: u.password_hash=generate_password_hash(new); db.session.commit(); flash('Palavra-passe alterada com sucesso.')
    return redirect(url_for('settings'))

# Migration helper: cria tabelas novas e acrescenta colunas em instalações antigas.
def migrate_schema():
    db.create_all()
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols or col.primary_key:
                continue
            typ = col.type.compile(db.engine.dialect)
            upper = typ.upper()
            if isinstance(col.type, db.Boolean):
                default = "FALSE"
            elif any(x in upper for x in ("INT", "REAL", "NUMERIC", "FLOAT", "DECIMAL", "DOUBLE")):
                default = "0"
            elif "CHAR" in upper or "TEXT" in upper:
                default = "''"
            else:
                default = None
            default_sql = f" DEFAULT {default}" if default is not None else ""
            sql = (
                f'ALTER TABLE "{table.name}" '
                f'ADD COLUMN IF NOT EXISTS "{col.name}" {typ}{default_sql}'
            )
            with db.engine.begin() as conn:
                conn.execute(text(sql))
            existing_cols.add(col.name)

def backup_database():
    try:
        if db.engine.url.get_backend_name()=='sqlite' and os.path.exists(DB_FILE):
            d=os.path.join(BASE_DIR,'backups'); os.makedirs(d,exist_ok=True); shutil.copy2(DB_FILE,os.path.join(d,'oficina_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.db'))
    except Exception: pass

with app.app_context():
    migrate_schema()
    if not Setting.query.first(): db.session.add(Setting())
    if not User.query.first():
        username=os.getenv('ADMIN_USERNAME','admin'); password=os.getenv('ADMIN_PASSWORD','JFauto123!')
        db.session.add(User(username=username,password_hash=generate_password_hash(password)))
    db.session.commit(); backup_database()

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.getenv('PORT','10000')), debug=False)
