
from datetime import date

from sqlalchemy import Column, Float, Integer, String

from database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)

    expense_date = Column(
        String(10),
        nullable=False,
        default=lambda: date.today().isoformat(),
    )
