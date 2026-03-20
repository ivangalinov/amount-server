from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    members: Mapped[list["WorkspaceUser"]] = relationship(
        "WorkspaceUser",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="workspace_users",
        back_populates="workspaces",
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    operations: Mapped[list["Operation"]] = relationship(
        "Operation",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


class WorkspaceUser(Base):
    __tablename__ = "workspace_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", backref="workspace_links")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
