# innes_cuarto_pruebas/bacnet_poller/polling.py

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from innes_cuarto_pruebas.bacnet_gateway.read_write import read_present_value

from .app import PollerApp


@dataclass
class PointBuffer:
    """Buffer circular de un punto (memoria)."""

    object_id_str: str
    window_size: int
    values: deque[dict[str, Any]]
    last_value: Any | None = None
    online: bool = True


def _get_or_create_point_buffer(poller: PollerApp, device_instance: int, object_id_str: str) -> PointBuffer:
    device_buffers = poller.point_buffers.setdefault(int(device_instance), {})
    buf = device_buffers.get(str(object_id_str))
    if buf:
        return buf

    window_size = int(poller.settings.get("window_size", 60))
    buf = PointBuffer(
        object_id_str=str(object_id_str),
        window_size=window_size,
        values=deque(maxlen=window_size),
        last_value=None,
        online=True,
    )
    device_buffers[str(object_id_str)] = buf
    return buf


async def poll_once(poller: PollerApp, *, device_instance: int, object_id_str: str) -> None:
    """Ejecuta una lectura best-effort y actualiza el buffer."""

    dev_state = poller.devices.get(int(device_instance))
    buf = _get_or_create_point_buffer(poller, int(device_instance), str(object_id_str))

    # Pausa automática si el dispositivo está offline o no existe en sesión
    if not dev_state or not dev_state.online:
        buf.online = False
        buf.last_value = None
        buf.values.append({"ts": time.time(), "value": None, "online": False})
        return

    s = poller.settings

    try:
        value = await read_present_value(
            poller.bacnet_app,
            device_ip=str(dev_state.ip),
            object_id_str=str(object_id_str),
            timeout_seconds=int(s.get("timeout_seconds", 5)),
        )
    except Exception:
        value = None

    buf.online = True
    buf.last_value = value
    buf.values.append({"ts": time.time(), "value": value, "online": True})


async def polling_loop(poller: PollerApp) -> None:
    """Loop principal de polling.

    Fuente de targets:
    - Django envía la selección de puntos (hasta 300) vía API del poller (/poll/targets).
    """

    interval_sec = float(poller.settings.get("poll_interval_sec", 5))

    while True:
        tasks: list[asyncio.Task] = []

        for device_instance, object_ids in poller.poll_targets.items():
            for object_id_str in object_ids:
                tasks.append(asyncio.create_task(poll_once(poller, device_instance=int(device_instance), object_id_str=str(object_id_str))))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        await asyncio.sleep(interval_sec)