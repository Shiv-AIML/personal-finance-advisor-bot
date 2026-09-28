# Personal Finance Advisor Bot

A beginner-friendly Flask capstone project for:
- User registration/login
- Income and expense tracking
- Category budgets
- Savings calculation
- Dashboard charts
- Monthly financial report
- Optional Gemini AI financial advisor

## 1. Create a virtual environment

Windows:
    python -m venv venv
    venv\Scripts\activate

macOS/Linux:
    python3 -m venv venv
    source venv/bin/activate

## 2. Install dependencies

    pip install -r requirements.txt

## 3. Configure environment

Copy `.env.example` to `.env`.

You can run the project without a Gemini API key. The AI page will show a helpful fallback message.
For Gemini, add your API key to `.env`:
    GEMINI_API_KEY=...

## 4. Run

    python app.py

Open:
    http://127.0.0.1:5000

## 5. Main pages

/                 Home
/register         Register
/login            Login
/dashboard        Dashboard
/income           Income
/expenses         Expenses
/budget           Budget
/analytics        Analytics
/advisor          AI Advisor
/report           Report

## 6. Demo flow

1. Register a user.
2. Add 2-3 income records.
3. Add several expenses in different categories.
4. Set category budgets.
5. Open Dashboard.
6. Open Analytics.
7. Open AI Advisor.
8. Open Report.

## Important

This is an educational capstone, not professional financial advice. Do not use the AI output as a guarantee of investment returns or financial outcomes.
