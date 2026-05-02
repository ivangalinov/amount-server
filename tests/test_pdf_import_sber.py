import os
import json
from operation.import_pdf import SBerPDFExtractor

current_dir = os.path.dirname(os.path.realpath(__file__))

mock_filepath = os.path.join(current_dir, 'resources', 'test_sber_import.pdf')

ref_path = os.path.join(current_dir, 'resources', 'sber_pdf_ref.json')


def get_ref() -> list[dict]:
    with open(ref_path, 'r', encoding='utf-8') as stream:
        return json.loads(stream.read())
    
def assert_dict(first: dict, second: dict):
    for key, value in first.items():
        if isinstance(value, dict):
            return assert_dict(value, second.get(key, {}))
        assert value == second.get(key)


def test_pdf_import_sber():
    with open(mock_filepath, 'rb') as stream:
        filedata = stream.read()

    extracted_data = SBerPDFExtractor().execute(filedata)


    assert len(extracted_data) != 0

    ref = get_ref()


    for data, ref_data in zip(extracted_data, ref):

        data['date'] = data['date'].strftime('%d.%m.%Y %H:%M')

        assert_dict(data, ref_data)
