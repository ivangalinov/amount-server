import pdfplumber
import io
from lib.date import parse_date

date_pattern = r'\b(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.\d{4}\b'

__all__ = ('PDFExtractor',)

class PDFExtractor:

    def execute(self, filedata: bytes) -> tuple:
        with pdfplumber.open(io.BytesIO(filedata)) as pdf:
            raw_result = ()
            buffer = []
            prev = None
            for page in pdf.pages:
                if self.reset_buffer_on_page():
                    buffer = []
                    prev = None
                text = (page.extract_text() or '').split('\n')
                for row in text:
                    if self.skip_row(row):
                        continue
                    if self.check_row(row):
                        if buffer and not self.union_callback(prev, row, buffer):
                            raw_result += (buffer.copy(),)
                            buffer.clear()
                        buffer.append(row)
                        prev = row
                    elif buffer and self.continuation_row(row, buffer):
                        buffer.append(row)
            if buffer and self.is_complete_group(buffer):
                raw_result += (buffer.copy(),)
            return tuple(map(self.build_row, raw_result))

    def skip_row(self, row: str) -> bool:
        return False

    def continuation_row(self, row: str, buffer: list[str]) -> bool:
        return False

    def is_complete_group(self, buffer: list[str]) -> bool:
        return bool(buffer)

    def reset_buffer_on_page(self) -> bool:
        return True

    def build_row(self, row: list[str]):
        return row

    def union_callback(self, prev: str, current: str, buffer: list[str]) -> bool:
        return False

    def check_row(self, row) -> bool:
        return True
