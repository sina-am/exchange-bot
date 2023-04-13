from aiohttp import web
import jinja2
from pkg.service import Service


def get_service(request: web.Request) -> Service:
    return request.app['service']


def get_jinja(request: web.Request) -> jinja2.Environment:
    return request.app['template_engine']
