
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from database import Base, get_db


# Create a separate in-memory database for testing.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# Make FastAPI use the test database instead of the real database.
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Smart Expense Tracker API!"
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_and_list_expense(client):
    response = client.post(
        "/expenses",
        json={
            "title": "Lunch",
            "amount": 150,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Lunch"
    assert response.json()["amount"] == 150
    assert response.json()["category"] == "Food"

    list_response = client.get("/expenses")

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["expenses"][0]["title"] == "Lunch"


def test_get_single_expense(client):
    create_response = client.post(
        "/expenses",
        json={
            "title": "Bus Ticket",
            "amount": 50,
            "category": "Travel",
            "expense_date": "2026-10-20",
        },
    )

    expense_id = create_response.json()["id"]

    response = client.get(f"/expenses/{expense_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Bus Ticket"


def test_update_expense(client):
    create_response = client.post(
        "/expenses",
        json={
            "title": "Lunch",
            "amount": 150,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )

    expense_id = create_response.json()["id"]

    response = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Dinner",
            "amount": 250,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Dinner"
    assert response.json()["amount"] == 250


def test_delete_expense(client):
    create_response = client.post(
        "/expenses",
        json={
            "title": "Coffee",
            "amount": 40,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )

    expense_id = create_response.json()["id"]

    response = client.delete(f"/expenses/{expense_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Expense deleted successfully"

    missing_response = client.get(f"/expenses/{expense_id}")
    assert missing_response.status_code == 404


def test_reject_negative_amount(client):
    response = client.post(
        "/expenses",
        json={
            "title": "Invalid Expense",
            "amount": -100,
            "category": "Food",
        },
    )

    assert response.status_code == 422


def test_nonexistent_expense_returns_404(client):
    response = client.get("/expenses/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Expense not found"


def test_expense_summary(client):
    client.post(
        "/expenses",
        json={
            "title": "Lunch",
            "amount": 150,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )
    client.post(
        "/expenses",
        json={
            "title": "Bus",
            "amount": 50,
            "category": "Travel",
            "expense_date": "2026-10-20",
        },
    )

    response = client.get("/reports/summary")

    assert response.status_code == 200
    assert response.json()["total_spending"] == 200
    assert response.json()["total_expenses"] == 2


def test_spending_by_category(client):
    client.post(
        "/expenses",
        json={
            "title": "Lunch",
            "amount": 150,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )
    client.post(
        "/expenses",
        json={
            "title": "Dinner",
            "amount": 250,
            "category": "Food",
            "expense_date": "2026-10-21",
        },
    )
    client.post(
        "/expenses",
        json={
            "title": "Bus",
            "amount": 50,
            "category": "Travel",
            "expense_date": "2026-10-20",
        },
    )

    response = client.get("/reports/by-category")

    assert response.status_code == 200

    categories = {
        item["category"]: item["total"]
        for item in response.json()["categories"]
    }

    assert categories["Food"] == 400
    assert categories["Travel"] == 50


def test_monthly_report(client):
    client.post(
        "/expenses",
        json={
            "title": "Lunch",
            "amount": 150,
            "category": "Food",
            "expense_date": "2026-10-20",
        },
    )
    client.post(
        "/expenses",
        json={
            "title": "Bus",
            "amount": 50,
            "category": "Travel",
            "expense_date": "2026-10-21",
        },
    )
    client.post(
        "/expenses",
        json={
            "title": "Book",
            "amount": 300,
            "category": "Education",
            "expense_date": "2026-09-15",
        },
    )

    response = client.get("/reports/monthly?year=2026&month=10")

    assert response.status_code == 200

    data = response.json()
    assert data["total_spending"] == 200
    assert data["total_expenses"] == 2


def test_reject_zero_amount(client):
    response = client.post(
        "/expenses",
        json={
            "title": "Invalid Expense",
            "amount": 0,
            "category": "Food",
        },
    )

    assert response.status_code == 422


def test_reject_missing_title(client):
    response = client.post(
        "/expenses",
        json={
            "amount": 100,
            "category": "Food",
        },
    )

    assert response.status_code == 422


def test_reject_invalid_month(client):
    response = client.get("/reports/monthly?year=2026&month=13")

    assert response.status_code == 400
    assert response.json()["detail"] == "Month must be between 1 and 12"


def test_reject_invalid_year(client):
    response = client.get("/reports/monthly?year=1999&month=10")

    assert response.status_code == 400
    assert response.json()["detail"] == "Year must be between 2000 and 2100"


def test_monthly_report_with_no_expenses(client):
    response = client.get("/reports/monthly?year=2026&month=10")

    assert response.status_code == 200
    assert response.json()["total_spending"] == 0
    assert response.json()["total_expenses"] == 0
    assert response.json()["expenses"] == []
