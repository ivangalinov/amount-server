"""
Пакет моделей по доменам. Импорт всех модулей регистрирует модели в Base.metadata.
Используется в database.init_db() и в Alembic.
"""
from __future__ import annotations

from category.model import Category, CategoryType
from operation.model import Operation
from user.model import User
from workspace.model import Workspace, WorkspaceUser

__all__ = [
    "Category",
    "CategoryType",
    "Operation",
    "User",
    "Workspace",
    "WorkspaceUser",
]
