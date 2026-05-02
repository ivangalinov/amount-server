import typing
from lib.pdf.extractor import PDFExtractor
from category.model import CategoryType
from .model import Operation
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

class CategoryMapper:

    def fetch() -> dict:
        pass

    def get() -> int:
        pass


class OperationImport:

    # def __init__(self):
    #     pass

    def extract_items(self, source: TSourceType, filedata: bytes, user_id: int) -> list[Operation]:
        extractor = extractor_factory.resolve(f'pdf.{source}')
        extracted_items = extractor.execute(filedata)
        category_mapper = CategoryMapper()
        category_mapper.fetch([item.get('category')] for item in extracted_items)
        result = []
        for item in extracted_items:
            if 'KOPILKA KARTA-VKLAD' in item['origin']:
                continue
            if item['type'] == CategoryType.INCOME:
                continue
            result.append(Operation(
                amount=item['amount'],
                category_id=category_mapper.get(item['category_id']),
                type=CategoryType.EXPENSE,
                created=item['date'],
                user_id=user_id,
                ext_key=item['ext_key'],
                ext_source=source,
            ))
        return result
