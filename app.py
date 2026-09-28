import os
from datetime import date, datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user, logout_user
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    entry_date = db.Column(db.Date, default=date.today, nullable=False)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), default="")
    entry_date = db.Column(db.Date, default=date.today, nullable=False)


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def money(value):
    return f"₹{value:,.2f}"


app.jinja_env.filters["money"] = money


def current_month():
    return date.today().strftime("%Y-%m")


def financial_summary(user_id):
    month = current_month()

    income_total = db.session.query(
        func.coalesce(func.sum(Income.amount), 0)
    ).filter(
        Income.user_id == user_id,
        func.strftime("%Y-%m", Income.entry_date) == month
    ).scalar() or 0

    expense_total = db.session.query(
        func.coalesce(func.sum(Expense.amount), 0)
    ).filter(
        Expense.user_id == user_id,
        func.strftime("%Y-%m", Expense.entry_date) == month
    ).scalar() or 0

    savings = income_total - expense_total
    savings_rate = (savings / income_total * 100) if income_total else 0

    category_rows = db.session.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        Expense.user_id == user_id,
        func.strftime("%Y-%m", Expense.entry_date) == month
    ).group_by(Expense.category).all()

    categories = {category: round(total, 2) for category, total in category_rows}
    return {
        "income": round(income_total, 2),
        "expenses": round(expense_total, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate, 2),
        "categories": categories,
        "month": month,
    }


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password should contain at least 6 characters.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    summary = financial_summary(current_user.id)
    recent_expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(Expense.entry_date.desc(), Expense.id.desc()).limit(8).all()

    return render_template(
        "dashboard.html",
        summary=summary,
        recent_expenses=recent_expenses,
    )


@app.route("/income", methods=["GET", "POST"])
@login_required
def income():
    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            source = request.form["source"].strip()
            entry_date = datetime.strptime(
                request.form["entry_date"], "%Y-%m-%d"
            ).date()
            if amount <= 0 or not source:
                raise ValueError
        except (ValueError, KeyError):
            flash("Enter a valid amount, source and date.", "danger")
            return redirect(url_for("income"))

        db.session.add(Income(
            user_id=current_user.id,
            amount=amount,
            source=source,
            entry_date=entry_date
        ))
        db.session.commit()
        flash("Income added.", "success")
        return redirect(url_for("income"))

    rows = Income.query.filter_by(
        user_id=current_user.id
    ).order_by(Income.entry_date.desc(), Income.id.desc()).all()

    return render_template("income.html", incomes=rows, today=date.today())


@app.route("/income/delete/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    row = Income.query.filter_by(id=income_id, user_id=current_user.id).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("Income deleted.", "success")
    return redirect(url_for("income"))


@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    categories = [
        "Food", "Transport", "Education", "Shopping",
        "Entertainment", "Healthcare", "Rent", "Bills", "Other"
    ]

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            category = request.form["category"]
            description = request.form.get("description", "").strip()
            entry_date = datetime.strptime(
                request.form["entry_date"], "%Y-%m-%d"
            ).date()
            if amount <= 0 or category not in categories:
                raise ValueError
        except (ValueError, KeyError):
            flash("Enter valid expense details.", "danger")
            return redirect(url_for("expenses"))

        db.session.add(Expense(
            user_id=current_user.id,
            amount=amount,
            category=category,
            description=description,
            entry_date=entry_date
        ))
        db.session.commit()
        flash("Expense added.", "success")
        return redirect(url_for("expenses"))

    rows = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(Expense.entry_date.desc(), Expense.id.desc()).all()

    return render_template(
        "expenses.html",
        expenses=rows,
        categories=categories,
        today=date.today()
    )


@app.route("/expenses/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    row = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for("expenses"))


@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget():
    categories = [
        "Food", "Transport", "Education", "Shopping",
        "Entertainment", "Healthcare", "Rent", "Bills", "Other"
    ]
    month = current_month()

    if request.method == "POST":
        try:
            category = request.form["category"]
            limit_amount = float(request.form["limit_amount"])
            if category not in categories or limit_amount <= 0:
                raise ValueError
        except (ValueError, KeyError):
            flash("Enter a valid budget.", "danger")
            return redirect(url_for("budget"))

        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category=category,
            month=month
        ).first()

        if existing:
            existing.limit_amount = limit_amount
        else:
            db.session.add(Budget(
                user_id=current_user.id,
                category=category,
                limit_amount=limit_amount,
                month=month
            ))

        db.session.commit()
        flash("Budget saved.", "success")
        return redirect(url_for("budget"))

    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=month
    ).all()

    budget_rows = []
    for b in budgets:
        spent = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.user_id == current_user.id,
            Expense.category == b.category,
            func.strftime("%Y-%m", Expense.entry_date) == month
        ).scalar() or 0

        budget_rows.append({
            "category": b.category,
            "limit": b.limit_amount,
            "spent": spent,
            "remaining": b.limit_amount - spent,
            "over": spent > b.limit_amount
        })

    return render_template(
        "budget.html",
        budgets=budget_rows,
        categories=categories,
        month=month
    )


@app.route("/analytics")
@login_required
def analytics():
    summary = financial_summary(current_user.id)
    return render_template("analytics.html", summary=summary)


@app.route("/advisor", methods=["GET", "POST"])
@login_required
def advisor():
    summary = financial_summary(current_user.id)
    advice = None

    if request.method == "POST":
        advice = generate_ai_advice(summary)

    return render_template("advisor.html", summary=summary, advice=advice)


@app.route("/report")
@login_required
def report():
    summary = financial_summary(current_user.id)
    return render_template("report.html", summary=summary, generated=date.today())


def generate_ai_advice(summary):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key or api_key == "your-gemini-api-key-here":
        return (
            "Gemini is not configured yet. Add GEMINI_API_KEY to your .env file. "
            "For now: review your highest spending category, keep expenses below "
            "income, and set category budgets before increasing discretionary spending."
        )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = f"""
You are an educational personal finance assistant.

Current month: {summary['month']}
Income: ₹{summary['income']}
Expenses: ₹{summary['expenses']}
Savings: ₹{summary['savings']}
Savings rate: {summary['savings_rate']}%
Category spending: {summary['categories']}

Give a concise, simple analysis with:
1. Spending observations
2. Possible overspending categories
3. A practical budget suggestion
4. Ways to improve savings
5. One emergency-fund reminder

Do not promise returns. Do not give instructions to buy or sell specific investments.
Clearly state that this is general educational information, not professional financial advice.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as exc:
        return (
            "AI service could not be reached right now. "
            "Check your Gemini API key and internet connection. "
            f"Technical detail: {type(exc).__name__}"
        )


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
