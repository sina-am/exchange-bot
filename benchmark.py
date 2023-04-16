from pkg.internal.requests import calc_latency, Request, schedule_request
import datetime
import logging
import multiprocessing

from aiohttp import web
import asyncio

format_time = "%Y/%m/%d %H:%M:%S.%f"


async def time_handler(request: web.Request):
    return web.json_response({
        'timeit': datetime.datetime.strftime(datetime.datetime.utcnow(), format_time)})


def run_test_server():
    app = web.Application()
    app.add_routes([
        web.get('/', time_handler),
        web.post('/post', time_handler),
    ])

    web.run_app(app, print=lambda _: None)


async def test_schedule_request_delay(n: int):
    min_latency = 0
    for i in range(5):
        latency = await calc_latency('get', 'http://localhost:8080/')
        if latency < min_latency or min_latency == 0:
            min_latency = latency

    avg = 0
    for i in range(n):
        deadline = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
        request = Request(method='get', url='http://localhost:8080')
        async with schedule_request(request, deadline, min_latency) as response:
            status, data = response.status, await response.json()

        actual_time = datetime.datetime.strptime(
            data['timeit'], format_time)  # type: ignore

        logging.info(f"request actually got to server at {actual_time}")
        timeit = actual_time - deadline
        assert timeit.total_seconds() > 0, "Before deadline"
        avg += timeit.total_seconds()

    print(f'avg using new_way: {avg/n}')


def main():
    logging.basicConfig(format="%(message)s", level=logging.WARNING)
    test_server = multiprocessing.Process(target=run_test_server, daemon=True)
    try:
        test_server.start()
        asyncio.run(test_schedule_request_delay(20))
        test_server.terminate()
    except KeyboardInterrupt:
        test_server.terminate()
        print(test_server.exitcode)


if __name__ == '__main__':
    main()
