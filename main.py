from fastapi import FastAPI

from auth import router as auth_router
from category import router as category_router
from database import init_db

app = FastAPI(title="Amount API")

# OpenAPI по умолчанию 3.1.0; часть клиентов/автодоков (Swagger в IDE и т.д.) ломается
# или не показывает операции. 3.0.2 — официально описанный в FastAPI обходной путь.
app.openapi_version = "3.0.2"

app.include_router(auth_router)
app.include_router(category_router)

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


# @app.get("/categories/income")
# async def list_income_categories(db: AsyncSession = Depends(get_db)) -> list[dict]:
#     """
#     Пример: все категории с типом income.
#     Запрос: select(Category).where(Category.type == CategoryType.INCOME)
#     """
#     result = await db.execute(select(Category).where(Category.type == CategoryType.INCOME))
#     categories = result.scalars().all()
#     return [
#         {"id": c.id, "name": c.name, "type": c.type.value, "workspace_id": c.workspace_id}
#         for c in categories
#     ]


def get_app() -> FastAPI:
    """
    Вспомогательная функция, если понадобится создавать приложение из других модулей.
    """
    return app

