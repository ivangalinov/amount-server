import typing
import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from lib.pdf.extractor import PDFExtractor
from category.model import CategoryType
from category.repository import CategoryRepository
from .sber import SBerPDFExtractor

TSourceType = typing.Literal['sber']

class PDFExtractorFactory:

    __extractors: dict[str, PDFExtractor]

    def __init__(self):
        self.__extractors = {}

    def register(self, key: str, extractor: PDFExtractor):
        self.__extractors[key] = extractor

    def resolve(self, key) -> PDFExtractor:
        if key not in self.__extractors:
            raise Exception('not found extractor')
        return self.__extractors[key]


extractor_factory = PDFExtractorFactory()
extractor_factory.register('pdf.sber', SBerPDFExtractor())

ext_categories_map = {
 'Автомобиль': 'Машина',
 'Все для дома': 'Дом',
 'Здоровье и красота': 'Здоровье',
 # 'Оплата по QR–коду СБП': '',
 'Отдых и развлечения': 'Досуг',
 # 'Перевод СБП',
 'Прочие операции': 'Прочее',
 'Прочие расходы': 'Прочее',
 'Рестораны и кафе': 'Рестораны',
 'Супермаркеты': 'Продукты'
}

class CategoryMapper:

    __repo: CategoryRepository
    __categories: dict[str, int]
    __category_to_ext_map: dict[str, str]

    def __init__(self, db: AsyncSession):
        self.__repo = CategoryRepository(db)
        self.__categories = {}

        self.__category_to_ext_map = {
            value: key for key, value in ext_categories_map.items()
        }

    async def fetch(self, ext_categories: list[str]):
        search_string = [
            ext_categories_map.get(ext)
            for ext in ext_categories
            if ext_categories_map.get(ext)
        ]

        categories = await self.__repo.get_list(
            dict(strict_search=search_string)
        )

        if not (items := categories['items']):
            return


        for category in items:
            self.__categories[self.__category_to_ext_map[category.name]] = category.id

    def get(self, ext_category: str) -> int | None:
        return self.__categories.get(ext_category)


class ImportOperationResult(typing.TypedDict):
    amount: float
    category_id: int | None
    type: CategoryType
    created: datetime.datetime
    ext_key: str
    ext_source: str
    origin: str
    errors: list[str] | None


class OperationImport:

    # def __init__(self):
    #     pass

    async def extract_items(self, db: AsyncSession, source: TSourceType, filedata: bytes) -> list[ImportOperationResult]:
        extractor = extractor_factory.resolve(f'pdf.{source}')
        extracted_items = extractor.execute(filedata)
        category_mapper = CategoryMapper(db)
        await category_mapper.fetch([item.get('category') for item in extracted_items])
        result: list[ImportOperationResult] = []
        for item in extracted_items:
            if 'KOPILKA KARTA-VKLAD' in item['origin']:
                continue
            if item['type'] == CategoryType.INCOME:
                continue
            result.append(ImportOperationResult(
                amount=item['amount'],
                category_id=category_mapper.get(item['category']),
                type=CategoryType.EXPENSE,
                created=item['date'],
                ext_key=item['ext_key'],
                ext_source=source,
                origin=item['origin'],
                errors=item['errors'],
            ))
        return result
