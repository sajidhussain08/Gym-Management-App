from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import os
load_dotenv()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///gym.db"
db = SQLAlchemy(app)
app.secret_key = os.getenv("SECRET_KEY")
app.permanent_session_lifetime = timedelta(minutes=30)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Auto-increment ID
    custom_id = db.Column(db.String(10), unique=True)  # GS001, etc.
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    plan_start = db.Column(db.Date, nullable=False)
    plan_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Active / Expired
    amount_paid = db.Column(db.Integer, nullable=False)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template('index.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = AdminUser.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session.permanent = True 
            session["admin_user"] = username
            return redirect("/dashboard") 
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "admin_user" not in session:
        return redirect("/login")
    return render_template('dash.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if "admin_user" not in session:
        return redirect("/login")
    if request.method == "POST":
        # 1. Get form data
        client_name = request.form['name'].strip()
        contact_number = request.form['phone'].strip()
        gender = request.form['gender']
        amount_paid = request.form['amount_paid'].strip()
        selected_plan = request.form['plan']

        # 2. Validate form data
        if Client.query.filter_by(phone=contact_number).first():
            return render_template("registration.html", error="Phone number already registered.")

        if not client_name.replace(" ", "").isalpha():
            return render_template("registration.html", error="Name should only contain letters.")

        if not contact_number.isdigit() or len(contact_number) != 10:
            return render_template("registration.html", error="Phone number must be 10 digits.")

        if gender not in ['Male', 'Female', 'Other']:
            return render_template("registration.html", error="Please select a valid gender.")

        if not selected_plan:
            return render_template("registration.html", error="Please select a subscription plan.")

        try:
            amount_paid = int(amount_paid)
            if amount_paid <= 0:
                raise ValueError
        except ValueError:
            return render_template("registration.html", error="Amount paid must be a positive number.")


        # 3. Generate custom ID like GS001, GS002 based on last client
        last_client = Client.query.order_by(Client.id.desc()).first()
        new_id_number = (last_client.id + 1) if last_client else 1
        new_id = f"GS{new_id_number:03d}"

         # 4. Determine plan dates
        plan_start = date.today()
        if selected_plan == "1month":
            plan_end = plan_start + relativedelta(months=1)
        elif selected_plan == "3months":
            plan_end = plan_start + relativedelta(months=3)
        elif selected_plan == "6months":
            plan_end = plan_start + relativedelta(months=6)
        elif selected_plan == "1year":
            plan_end = plan_start + relativedelta(months=12)


        # 5. Determine status
        status = "Active" if plan_end >= date.today() else "Expired"

        # 6. Create new client
        new_client = Client(
            custom_id=new_id,
            name=client_name,
            phone=contact_number,
            gender=gender,
            plan_start=plan_start,
            plan_end=plan_end,
            status=status,
            amount_paid=amount_paid
        )

        # 7. Save to database
        db.session.add(new_client)
        db.session.commit()

        return redirect("/clients-overview")
    
    return render_template("registration.html")

@app.route("/renew", methods = ['GET', 'POST'])
def renew():
    if "admin_user" not in session:
        return redirect("/login")
    
    if request.method == 'POST':
        custom_id = request.form['custom_id'].strip()
        selected_plan = request.form['plan']
        amount_paid = request.form['amount_paid'].strip()
        
        if not custom_id:
            return render_template("renew.html", error="Client ID is required.")
        if not selected_plan:
            return render_template("renew.html", error="Please select a subscription plan.")
        try:
            amount_paid = int(amount_paid)
            if amount_paid <= 0:
                raise ValueError
        except ValueError:
            return render_template("renew.html", error="Amount paid must be a positive number.")        

        client = Client.query.filter_by(custom_id=custom_id).first()

        if not client:
            return render_template("renew.html", error=f"No client found with ID {custom_id}")
        if client.plan_end >= date.today():
            plan_start = client.plan_end
        else:
            plan_start = date.today()
            
        if selected_plan == "1month":
            plan_end = plan_start + relativedelta(months=1)
        elif selected_plan == "3months":
            plan_end = plan_start + relativedelta(months=3)
        elif selected_plan == "6months":
            plan_end = plan_start + relativedelta(months=6)
        elif selected_plan == "1year":
            plan_end = plan_start + relativedelta(months=12)


        client.plan_start = plan_start
        client.plan_end = plan_end
        client.status = "Active" if plan_end >= date.today() else "Expired"
        client.amount_paid = amount_paid

        db.session.commit()

        return redirect("/clients-overview")
    return render_template("renew.html")

@app.route("/clients-overview")
def clients_overview():
    if "admin_user" not in session:
        return redirect("/login")
    clients = Client.query.all()
    for client in clients:
        if client.plan_end < date.today():
            client.status = "Expired"
        else:
            client.status = "Active"
    db.session.commit()
    return render_template("clients overview.html", clients = clients)

@app.route("/active-clients")
def active_clients():
    if "admin_user" not in session:
        return redirect("/login")
    today = date.today()
    #Get only clients whose plan is still valid
    clients = Client.query.filter(Client.plan_end>=today).all()
    return render_template("active clients.html", clients = clients)

@app.route("/inactive-clients")
def inactive_clients():
    if "admin_user" not in session:
        return redirect("/login")
    today = date.today()
    #Get Only clients whose plan is expired
    clients = Client.query.filter(Client.plan_end<today).all()
    return render_template("inactive clients.html",clients = clients)

@app.route("/expiring-clients")
def expiring_clients():
    if "admin_user" not in session:
        return redirect("/login")
    today = date.today()
    in_two_days = today + timedelta(days=2)
    #Get only clients whose plan is going to expire in 2days
    clients = Client.query.filter(Client.plan_end >= today, Client.plan_end <= in_two_days).all()
    return render_template("expiring clients.html", clients = clients)

@app.route('/logout')
def logout():
    session.pop('admin_user', None)  # Remove admin_user from session
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug = True)