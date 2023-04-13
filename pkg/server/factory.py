import logging
from aiohttp import web

from pkg.service import Service
from pkg.server.apis import router as api_router
from pkg.server.middleware import error_middleware


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_server(service: Service) -> web.Application:
    app = web.Application(middlewares=[error_middleware])
    app['service'] = service
    app.add_routes(api_router)
    app.add_routes([web.static('/static/', './statics')])
    return app
