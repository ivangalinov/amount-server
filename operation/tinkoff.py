import re

from lib.date import parse_date
from lib.pdf.extractor import PDFExtractor
from category.model import CategoryType
from .sber import TOperationRaw

row_start_pattern = re.compile(
    r'^(\d{2}\.\d{2}\.\d{4}) (\d{2}\.\d{2}\.\d{4}) '
    r'(-[\d ]+\.\d{2}) ₽ (-[\d ]+\.\d{2}) ₽ (.+) (\d{4})$'
)
time_line_pattern = re.compile(r'^(\d{2}:\d{2}) \d{2}:\d{2}(?: .+)?$')
skip_line_pattern = re.compile(r'^АО «ТБанк»|^БИК ')


def parse_amount(amount_str: str) -> float:
    return float(amount_str.replace(' ', ''))


def format_amount_key(amount_str: str) -> str:
    return amount_str.replace(' ', '')


class TTinkoffPDFExtractor(PDFExtractor):

    def skip_row(self, row: str) -> bool:
        if skip_line_pattern.match(row):
            return True
        stripped = row.strip()
        if stripped.isdigit() and len(stripped) <= 2:
            return True
        return len(stripped) <= 2 and stripped.isalpha()

    def check_row(self, row: str) -> bool:
        return bool(row_start_pattern.match(row))

    def continuation_row(self, row: str, buffer: list[str]) -> bool:
        return bool(buffer)

    def reset_buffer_on_page(self) -> bool:
        return False

    def union_callback(self, prev: str, current: str, buffer: list[str]) -> bool:
        return False

    def build_row(self, row: list[str]) -> TOperationRaw:
        errors: set[str] = set()
        first = row[0]
        match = row_start_pattern.match(first)
        if not match:
            errors.add('row')
            return dict(
                date=None,
                amount=0.0,
                category=None,
                ext_key='',
                type=CategoryType.EXPENSE,
                origin='\n'.join(row),
                errors=list(errors),
            )

        op_date = match.group(1)
        card_amount_str = match.group(4)
        card = match.group(6)

        op_time = ''
        if len(row) > 1:
            time_match = time_line_pattern.match(row[1])
            if time_match:
                op_time = time_match.group(1)

        if not op_time:
            errors.add('date')

        amount_value = None
        amount_key = ''
        try:
            amount_value = parse_amount(card_amount_str)
            amount_key = format_amount_key(card_amount_str)
        except ValueError:
            errors.add('amount')

        operation_type = (
            CategoryType.INCOME if amount_value is not None and amount_value > 0
            else CategoryType.EXPENSE
        )
        if amount_value is not None and operation_type == CategoryType.EXPENSE:
            amount_value *= -1

        parsed_date = None
        if op_time and not errors.intersection({'date'}):
            try:
                parsed_date = parse_date(f'{op_date} {op_time}')
            except ValueError:
                errors.add('date')

        ext_key = f'{op_date}_{op_time}_{amount_key}_{card}' if amount_key else ''

        return dict(
            date=parsed_date,
            amount=amount_value if amount_value is not None else 0.0,
            category=None,
            ext_key=ext_key,
            type=operation_type,
            origin='\n'.join(row),
            errors=list(errors),
        )
