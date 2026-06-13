import os
from unittest.mock import AsyncMock, patch

import pytest

from operation.import_pdf import CategoryMapper, OperationImport

current_dir = os.path.dirname(os.path.realpath(__file__))
tinkoff_pdf_path = os.path.join(current_dir, 'resources', 'test_tinn_import.pdf')

pytestmark = pytest.mark.skipif(
    not os.path.isfile(tinkoff_pdf_path),
    reason='test fixtures missing: tests/resources/test_tinn_import.pdf',
)


@pytest.mark.asyncio
async def test_category_mapper_fetch_ignores_empty_categories(session_factory):
    async with session_factory() as db:
        mapper = CategoryMapper(db)
        with patch.object(
            mapper._CategoryMapper__repo,
            'get_list',
            new_callable=AsyncMock,
        ) as get_list:
            await mapper.fetch([''] * 10)
            get_list.assert_not_called()


@pytest.mark.asyncio
async def test_tinkoff_import_items_have_no_category_id(session_factory):
    with open(tinkoff_pdf_path, 'rb') as stream:
        filedata = stream.read()

    async with session_factory() as db:
        items = await OperationImport().extract_items(db, 'tinkoff', filedata)

    assert len(items) == 113
    assert all(item['category_id'] is None for item in items)


@pytest.mark.asyncio
async def test_import_tinkoff_route(authenticated_client):
    with open(tinkoff_pdf_path, 'rb') as stream:
        response = await authenticated_client.post(
            '/operation/import',
            params={'source': 'tinkoff'},
            files={'file': ('test_tinn_import.pdf', stream.read(), 'application/pdf')},
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body['items']) == 113
    assert all(item['category_id'] is None for item in body['items'])
