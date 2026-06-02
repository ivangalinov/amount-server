import typing
import datetime
import re
from lib.date import parse_date
from lib.pdf.extractor import PDFExtractor
from category.model import CategoryType

date_pattern = r'\b(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.\d{4}\b'
amount_pattern = r'\b\d+,\d{2}\b'

category_and_amount_pattern = r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2} (.+?) ([+-]?)(\d{1,3}(?: \d{3})*,\d{2})'

class TOperationRaw(typing.TypedDict):
    date: datetime.datetime
    amount: float
    category: str
    ext_key: str
    origin: str
    errors: list[str]
    type: CategoryType


def parse_category_and_amount(raw_str: str) -> tuple[str, float, CategoryType]:
    match = re.search(category_and_amount_pattern, raw_str)
    if not match:
        return None, None
    category = match.group(1)
    sign = match.group(2)
    cost_str = match.group(3)
    
    type = CategoryType.EXPENSE if sign != '+' else CategoryType.INCOME
    # Преобразуем в число с плавающей точкой (убираем пробелы, заменяем запятую на точку)
    amount = float(cost_str.replace(' ', '').replace(',', '.'))
    return category, amount, type


class SBerPDFExtractor(PDFExtractor):

    def check_row(self, row):
        return re.match(date_pattern, row)

    def union_callback(self, prev: str, current: str, buffer: list[str]):
        return len(buffer) == 1
    
    def build_row(self, row) -> TOperationRaw:
        errors = set()
        [first, second] = row
        splited_first = first.split(' ')
        splitted_second = second.split(' ')
        date = splited_first[0]
        time = splited_first[1]

        category, amount, type = parse_category_and_amount(first)
        if not amount:
            errors.add('amount')
        if not category:
            errors.add('category')
        if type == CategoryType.EXPENSE:
            amount *= -1
        ext_key = splitted_second[1]
        return dict(
            date=parse_date(f'{date} {time}'),
            amount=amount,
            category=category,
            ext_key=ext_key,
            type=type,
            origin='\n'.join(row),
            errors=list(errors),
        )

