import pdfplumber
import io
from lib.date import parse_date

date_pattern = r'\b(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.\d{4}\b'

__all__ = ('PDFExtractor',)

class PDFExtractor:

    def execute(self, filedata: bytes) -> tuple:
        with pdfplumber.open(io.BytesIO(filedata)) as pdf:
            raw_result = ()
            for page in pdf.pages:
                text = page.extract_text().split('\n')
                row_count = len(text) - 1
                buffer = []
                prev = None
                for inx, row in enumerate(text):
                    if not self.check_row(row):
                        continue
                    is_last = inx == row_count
                    if prev and not self.union_callback(prev, row, buffer) or is_last:
                        raw_result += (buffer.copy(),)
                        buffer.clear()
                    buffer.append(row)
                    prev = row
            
            return tuple(map(lambda row: self.build_row(row), raw_result))

    def build_row(self, row: list[str]):
        return row

    def union_callback(self, prev: str, current: str) -> bool:
        return False

    def check_row(self, row) -> bool:
        return True
