
# Smart Expense Tracker API

A REST API built using Python, FastAPI, SQLAlchemy, and SQLite.

## Features
- Create, view, update, and delete expenses
- Store expenses in SQLite
- Validate expense details
- Generate total spending summaries
- View spending by category
- Generate monthly reports
- Interactive API documentation with Swagger UI

## Technologies
- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Uvicorn

## Run Locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the server:

```bash
python -m uvicorn app:app
```

Open Swagger UI:

http://127.0.0.1:8000/docs
