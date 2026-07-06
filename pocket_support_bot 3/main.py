import asyncio
import uvicorn

from config import POSTBACK_PORT
from db import init_db
from bot import start_bot_polling
from postback import app as postback_app


async def start_postback_server():
    config = uvicorn.Config(
        postback_app, host="0.0.0.0", port=POSTBACK_PORT, log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await init_db()
    await asyncio.gather(
        start_bot_polling(),
        start_postback_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
