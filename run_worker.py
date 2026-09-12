import asyncio
import selectors

from arq.worker import Worker

from app.workers.worker import WorkerSettings


def main():
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())

    try:
        asyncio.set_event_loop(loop)

        worker = Worker(
            functions=WorkerSettings.functions,
            redis_settings=WorkerSettings.redis_settings,
        )

        worker.run()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
