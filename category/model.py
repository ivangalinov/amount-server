from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SqlEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    limit: Mapped[str | None] = mapped_column(String, nullable=True)

    type: Mapped[CategoryType] = mapped_column(
        SqlEnum(CategoryType, name="category_type"),
        nullable=False,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    color: Mapped[str] = mapped_column(String, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="categories")
    user: Mapped["User | None"] = relationship("User", back_populates="categories")
    operations: Mapped[list["Operation"]] = relationship(
        "Operation",
        back_populates="category",
        cascade="all, delete-orphan",
    )
