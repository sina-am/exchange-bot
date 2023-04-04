import json
import logging
from typing import Optional

import pydantic


class StorageConfig(pydantic.BaseSettings):
    url: str = 'sqlite+pysqlite:///data/sqlite.db'


class ServerConfig(pydantic.BaseSettings):
    host: str = 'localhost'
    port: int = 8080


class LoggingConfig(pydantic.BaseSettings):
    level: int = logging.INFO
    format: str = '[%(levelname)s] %(asctime)s: %(message)s'
    file: Optional[str] = None


class CaptchaConfig(pydantic.BaseSettings):
    model: str = './data/cfl.model'
    training_dir: str = './data/captcha/training'


class MainConfig(pydantic.BaseSettings):
    storage: StorageConfig = StorageConfig()
    server: ServerConfig = ServerConfig()
    logging: LoggingConfig = LoggingConfig()
    captcha: CaptchaConfig = CaptchaConfig()


def get_config() -> MainConfig:
    with open('./data/config.json', 'r') as fd:
        return MainConfig(**json.load(fd))
