import os
import asyncio
import logging
from aiohttp import web
from typing import Optional, get_args

import typer

from pkg.config import get_config
from pkg.internal.brokers import TavanaBroker
from pkg.internal.captcha import CaptchaSolver
from pkg.models import BrokerName
from pkg.server.factory import create_server
from pkg.service import Service
from pkg.storage import SqliteStorage

srv_cli = typer.Typer()
captcha_cli = typer.Typer()
cli = typer.Typer()
cli.add_typer(
    srv_cli,
    name='service',
    help='Interact with service layer directly'
)
cli.add_typer(
    captcha_cli,
    name='captcha',
    help='Predict and train captcha model'
)


@srv_cli.command('login')
def login(broker: str, username: str, password: str):
    assert broker in get_args(BrokerName)
    config = get_config()

    ml = CaptchaSolver()
    ml.load(config.captcha.model)

    service = Service(
        storage=SqliteStorage(config.storage.url),
        brokers={
            "TAVANA": TavanaBroker(ml),
        }
    )

    try:
        account = asyncio.run(
            service.login(broker, username, password))  # type: ignore
        print('account id:', account.id)
    except Exception as exc:
        print(exc)


@srv_cli.command('balance')
def account_balance(username: str):
    config = get_config()

    ml = CaptchaSolver()
    ml.load(config.captcha.model)

    service = Service(
        storage=SqliteStorage(config.storage.url),
        brokers={
            "TAVANA": TavanaBroker(ml),
        }
    )

    try:
        balance = asyncio.run(service.get_account_balance(username))
        print(f'account balance is: {balance}IRR')
    except Exception as exc:
        print(exc)


@cli.command('migrate')
def migrate(url: Optional[str] = None):
    """ Migrate database """

    config = get_config()

    if not url:
        url = config.storage.url

    storage = SqliteStorage(url)
    storage.migrate()


@captcha_cli.command('train')
def captcha_train(training_dir: Optional[str] = None, model: Optional[str] = None):
    """ Train captcha model """

    config = get_config()
    if not training_dir:
        training_dir = config.captcha.training_dir
    if not model:
        model = config.captcha.model

    ml = CaptchaSolver()
    ml.train_model(training_dir)
    ml.save(model)


@captcha_cli.command('predict')
def captcha_predict(filepath: str):
    config = get_config()
    ml = CaptchaSolver()
    ml.load(config.captcha.model)
    with open(filepath, 'rb') as fd:
        print("Predicted:", ml.predict(fd))
    ml.save(config.captcha.model)


@cli.command('serve')
def serve():
    """ Serve APIs """
    os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '0'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'
    config = get_config()

    logging.basicConfig(
        format=config.logging.format,
        level=config.logging.level
    )

    ml = CaptchaSolver()
    ml.load(config.captcha.model)

    app = create_server(
        service=Service(
            storage=SqliteStorage(config.storage.url),
            brokers={
                "TAVANA": TavanaBroker(ml),
            }
        )
    )
    logging.info(f"server is running on http://{config.server.host}:{config.server.port}")
    web.run_app(
        app,
        host=config.server.host,
        port=config.server.port,
        print=lambda _: None,
        reuse_address=True
    )
    logging.info(f"server is shutting down")
