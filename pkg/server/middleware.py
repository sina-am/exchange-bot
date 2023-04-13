import json
from typing import Any, Dict, List, Literal, Union
import pydantic
from aiohttp import web
from pkg.storage import StorageError
from pkg.internal.brokers import BrokerError
from dataclasses import dataclass, asdict

ErrorLevel = Literal["STORAGE", "BROKER", "SERVICE", "JSON", "VALIDATION", "HTTP"]


@dataclass
class ErrorResponse:
    level: ErrorLevel
    message: Union[Dict[str, Any], List[Any], str]

    def __dir__(self):
        return asdict(self)


@web.middleware
async def error_middleware(request: web.Request, handler) -> web.Response:
    if not request.path.startswith('/api'):
        return await handler(request)

    try:
        return await handler(request)
    except web.HTTPException as exc:
        return web.json_response(
            data=asdict(ErrorResponse(level="HTTP", message=exc.reason)),
            status=exc.status
        )
    except json.JSONDecodeError as exc:
        return web.json_response(
            data=asdict(ErrorResponse(level="JSON", message=str(exc))),
            status=400
        )
    except pydantic.ValidationError as exc:
        return web.json_response(
            asdict(ErrorResponse(level="VALIDATION", message=exc.errors())),
            status=422
        )
    except StorageError as exc:
        return web.json_response(
            asdict(ErrorResponse(level="STORAGE", message=str(exc))),
            status=400
        )
    except BrokerError as exc:
        return web.json_response(
            asdict(ErrorResponse(level="BROKER", message=str(exc))),
            status=400
        )
    except Exception as exc:
        raise exc
