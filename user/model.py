from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        secondary="workspace_users",
        back_populates="users",
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    operations: Mapped[list["Operation"]] = relationship(
        "Operation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
