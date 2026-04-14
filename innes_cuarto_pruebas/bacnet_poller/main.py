# innes_cuarto_pruebas/bacnet_poller/main.py

from __future__ import annotations

import asyncio
import logging

import uvicorn

from innes_cuarto_pruebas.settings import BACNET_DEFAULTS

from innes_cuarto_pruebas.bacnet_gateway.client import (
    create_bacnet_application,
    close_bacnet_application,
)

from .api import create_api
from .app import PollerApp
from .discovery import run_discovery_once
from .polling import polling_loop


logger = logging.getLogger("bacnet_poller")


async def discovery_loop(poller: PollerApp) -> None:
    interval = int(poller.settings.get("discovery_interval_sec", 30))

    while True:
        try:
            await run_discovery_once(poller)
        except Exception as e:
            logger.exception("discovery_loop error=%s", str(e))

        await asyncio.sleep(interval)


async def run_server() -> None:
    # Settings efectivos (en esta fase vienen de defaults)
    settings = dict(BACNET_DEFAULTS)

    # Crear app BACnet (socket único)
    bacnet_app = await create_bacnet_application(
        bind_ip=str(settings.get("bind_ip")),
        mask=str(settings.get("mask", "24")),
        local_port=int(settings.get("local_port", 47808)),
        bbmd_enabled=bool(settings.get("bbmd_enabled", False)),
        bbmd_address=settings.get("bbmd_address"),
        foreign_device_enabled=bool(settings.get("foreign_device_enabled", False)),
        foreign_device_bbmd_address=settings.get("foreign_device_bbmd_address"),
        foreign_device_ttl_seconds=int(settings.get("foreign_device_ttl_seconds", 600)),
    )

    poller = PollerApp(settings=settings, bacnet_app=bacnet_app)

    # API
    api = create_api(poller)

    # Background tasks
    asyncio.create_task(discovery_loop(poller))
    asyncio.create_task(polling_loop(poller))

    # Uvicorn server (en el mismo loop)
    config = uvicorn.Config(api, host="127.0.0.1", port=8001, log_level="info")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        await close_bacnet_application(bacnet_app)


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()