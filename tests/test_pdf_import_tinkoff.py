import os
import json

import pytest

from operation.import_pdf import TTinkoffPDFExtractor

current_dir = os.path.dirname(os.path.realpath(__file__))

mock_filepath = os.path.join(current_dir, 'resources', 'test_tinn_import.pdf')

ref_path = os.path.join(current_dir, 'resources', 'tinkoff_pdf_ref.json')

pytestmark = pytest.mark.skipif(
    not os.path.isfile(mock_filepath) or not os.path.isfile(ref_path),
    reason=(
        'test fixtures missing: '
        'tests/resources/test_tinn_import.pdf and tinkoff_pdf_ref.json'
    ),
)


def get_ref() -> list[dict]:
    with open(ref_path, 'r', encoding='utf-8') as stream:
        return json.loads(stream.read())


def assert_dict(first: dict, second: dict):
    for key, value in first.items():
        if isinstance(value, dict):
            return assert_dict(value, second.get(key, {}))
        assert value == second.get(key)


def test_pdf_import_tinkoff():
    with open(mock_filepath, 'rb') as stream:
        filedata = stream.read()

    extracted_data = TTinkoffPDFExtractor().execute(filedata)

    assert len(extracted_data) == 121

    ref = get_ref()

    for data, ref_data in zip(extracted_data, ref):
        data['date'] = data['date'].strftime('%d.%m.%Y %H:%M')
        assert_dict(data, ref_data)
        assert data['category'] is None


def test_pdf_import_tinkoff_categories_are_empty():
    with open(mock_filepath, 'rb') as stream:
        filedata = stream.read()

    extracted_data = TTinkoffPDFExtractor().execute(filedata)

    assert all(item['category'] is None for item in extracted_data)
