"""Private MCP bridge to the same read-only, published API views used by Angular."""
import json
from typing import Any, Literal

import anyio
from pydantic import BaseModel

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections
from django.test import RequestFactory
from mcp import Client
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import views

Section = Literal['perfil', 'proyectos', 'experiencias', 'formacion', 'tecnologias', 'enlaces']
Language = Literal['es', 'en']
SECTIONS = ('perfil', 'proyectos', 'experiencias', 'formacion', 'tecnologias', 'enlaces')


class PublicData(BaseModel):
    data: dict[str, Any]


def read_public_section(section: str, language: str) -> dict:
    readers = {
        'perfil': views.perfil_publico, 'proyectos': views.proyectos_publicos,
        'experiencias': views.experiencias_publicas, 'formacion': views.formacion_publica,
        'tecnologias': views.tecnologias_publicas, 'enlaces': views.enlaces_publicos,
    }
    if section not in readers or language not in ('es', 'en'):
        raise ValueError('Unsupported public resource')
    host = settings.ALLOWED_HOSTS[0].lstrip('.') if settings.ALLOWED_HOSTS else 'localhost'
    request = RequestFactory().get(f'/api/v1/{section}/',
                                   {'lang': language, 'page_size': 100}, HTTP_HOST=host)
    close_old_connections()
    try:
        response = readers[section](request)
        if response.status_code == 404 and section == 'perfil':
            return {'available': False}
        if response.status_code != 200:
            raise ValueError('Public API unavailable')
        data = json.loads(response.content)
        if 'results' in data:
            if data.get('next'):
                raise ValueError('Public context exceeds the bounded snapshot')
            return {'results': data['results']}
        return data
    finally:
        close_old_connections()


def create_server() -> MCPServer:
    server = MCPServer('Aubar Portfolio', log_level='ERROR')

    @server.tool(structured_output=True, annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False,
                                             idempotent_hint=True, open_world_hint=False))
    async def consultar_portfolio(seccion: Section, idioma: Language = 'es') -> PublicData:
        """Read published portfolio data only. Never access drafts, credentials or the Admin."""
        data = await sync_to_async(read_public_section, thread_sensitive=True)(seccion, idioma)
        return PublicData(data=data)

    return server


async def public_snapshot(language: Language) -> dict:
    """SDK memory transport performs real MCP discovery/calls without extra ports or processes."""
    with anyio.fail_after(8):
        return await _public_snapshot(language)


async def _public_snapshot(language: Language) -> dict:
    async with Client(create_server(), read_timeout_seconds=8) as client:
        discovered = await client.list_tools()
        if [tool.name for tool in discovered.tools] != ['consultar_portfolio']:
            raise ValueError('Unexpected MCP tools')
        snapshot = {}
        for section in SECTIONS:
            result = await client.call_tool('consultar_portfolio', {'seccion': section, 'idioma': language})
            if result.is_error or result.structured_content is None:
                raise ValueError('MCP source unavailable')
            snapshot[section] = result.structured_content['data']
        return snapshot
