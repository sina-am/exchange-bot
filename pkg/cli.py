import asyncio
import logging
from typing import Optional, get_args

import typer

from pkg.config import get_config
from pkg.internal.brokers import TavanaBroker
from pkg.internal.captcha import CaptchaML
from pkg.models import BrokerName
from pkg.server import WebServer
from pkg.service import Service
from pkg.storage import SqliteStorage

srv_cli = typer.Typer()


@srv_cli.command('login')
def login(broker: str, username: str, password: str):
    assert broker in get_args(BrokerName)
    config = get_config()

    ml = CaptchaML()
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

    ml = CaptchaML()
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


cli = typer.Typer()
cli.add_typer(
    srv_cli,
    name='service',
    help='Interact with service layer directly'
)


@cli.command('migrate')
def migrate(url: Optional[str] = None):
    """ Migrate database """

    config = get_config()

    if not url:
        url = config.storage.url

    storage = SqliteStorage(url)
    storage.migrate()


@cli.command('captcha')
def captcha_train(training_dir: Optional[str] = None, model: Optional[str] = None):
    """ Train captcha model """

    config = get_config()
    if not training_dir:
        training_dir = config.captcha.training_dir
    if not model:
        model = config.captcha.model

    ml = CaptchaML()

    print("training captcha model")
    ml.train_model(training_dir)
    ml.save(model)


@cli.command('serve')
def serve():
    """ Serve APIs """

    config = get_config()

    logging.basicConfig(
        format=config.logging.format,
        level=config.logging.level
    )

    ml = CaptchaML()
    ml.load(config.captcha.model)

    server = WebServer(
        host=config.server.host,
        port=config.server.port,
        service=Service(
            storage=SqliteStorage(config.storage.url),
            brokers={
                "TAVANA": TavanaBroker(ml),
            }
        )
    )

    server.run()
