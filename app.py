
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Expense


# Create database tables if they do not exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Expense Tracker API",
    description="API to create, view, update, delete, and report expenses.",
    version="3.0.0",
)


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# REQUEST AND RESPONSE MODELS
# -------------------------

class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=50)
    expense_date: date | None = None


class ExpenseUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=50)
    expense_date: date | None = None


class ExpenseResponse(BaseModel):
    id: int
    title: str
    amount: float
    category: str
    expense_date: date

    model_config = ConfigDict(from_attributes=True)


# -------------------------
# HOME AND HEALTH ENDPOINTS
# -------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to the Smart Expense Tracker API!"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# -------------------------
# CREATE: ADD AN EXPENSE
# -------------------------

@app.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=201,
)
def create_expense(
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
):
    new_expense = Expense(
        title=expense_data.title.strip(),
        amount=expense_data.amount,
        category=expense_data.category.strip(),
        expense_date=(
            expense_data.expense_date.isoformat()
            if expense_data.expense_date
            else date.today().isoformat()
        ),
    )

    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    return new_expense


# -------------------------
# READ: GET ALL EXPENSES
# -------------------------

@app.get("/expenses")
def get_all_expenses(db: Session = Depends(get_db)):
    expenses = (
        db.query(Expense)
        .order_by(Expense.id)
        .all()
    )

    return {
        "total": len(expenses),
        "expenses": expenses,
    }


# -------------------------
# READ: GET ONE EXPENSE
# -------------------------

@app.get(
    "/expenses/{expense_id}",
    response_model=ExpenseResponse,
)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
):
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id)
        .first()
    )

    if expense is None:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    return expense


# -------------------------
# UPDATE: MODIFY AN EXPENSE
# -------------------------

@app.put(
    "/expenses/{expense_id}",
    response_model=ExpenseResponse,
)
def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    db: Session = Depends(get_db),
):
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id)
        .first()
    )

    if expense is None:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    expense.title = expense_data.title.strip()
    expense.amount = expense_data.amount
    expense.category = expense_data.category.strip()

    if expense_data.expense_date is not None:
        expense.expense_date = (
            expense_data.expense_date.isoformat()
        )

    db.commit()
    db.refresh(expense)

    return expense


# -------------------------
# DELETE: REMOVE AN EXPENSE
# -------------------------

@app.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
):
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id)
        .first()
    )

    if expense is None:
        raise HTTPException(
            status_code=404,
            detail="Expense not found",
        )

    db.delete(expense)
    db.commit()

    return {
        "message": "Expense deleted successfully"
    }


# -------------------------
# REPORT 1: SUMMARY
# -------------------------

@app.get("/reports/summary")
def expense_summary(db: Session = Depends(get_db)):
    total = (
        db.query(
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .scalar()
    )

    count = db.query(Expense).count()

    return {
        "total_spending": total,
        "total_expenses": count,
    }


# -------------------------
# REPORT 2: CATEGORY REPORT
# -------------------------

@app.get("/reports/by-category")
def spending_by_category(db: Session = Depends(get_db)):
    results = (
        db.query(
            Expense.category,
            func.sum(Expense.amount).label("total"),
        )
        .group_by(Expense.category)
        .order_by(Expense.category)
        .all()
    )

    return {
        "categories": [
            {
                "category": category,
                "total": total,
            }
            for category, total in results
        ]
    }


# -------------------------
# REPORT 3: MONTHLY REPORT
# -------------------------

@app.get("/reports/monthly")
def monthly_report(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    if year < 2000 or year > 2100:
        raise HTTPException(
            status_code=400,
            detail="Year must be between 2000 and 2100",
        )

    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12",
        )

    date_prefix = f"{year:04d}-{month:02d}-"

    expenses = (
        db.query(Expense)
        .filter(
            Expense.expense_date.like(
                f"{date_prefix}%"
            )
        )
        .order_by(Expense.expense_date)
        .all()
    )

    total = sum(expense.amount for expense in expenses)

    return {
        "year": year,
        "month": month,
        "total_spending": total,
        "total_expenses": len(expenses),
        "expenses": expenses,
    }
