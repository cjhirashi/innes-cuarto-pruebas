# innes_cuarto_pruebas/bacnet_poller/discovery.py

from __future__ import annotations

import time
from typing import Any

from innes_cuarto_pruebas.bacnet_gateway.discover import discover_devices

from .app import PollerApp


async def run_discovery_once(poller: PollerApp, low_limit=None, high_limit=None) -> dict[str, Any]:
    """Ejecuta un ciclo de discovery y actualiza el estado en memoria."""

    # 1) Preparación: todos podrían volverse offline si no responden
    poller.mark_all_devices_offline_cycle_increment()

    # 2) Who-Is/I-Am sobre socket único
    s = poller.settings
    devices = await discover_devices(
        poller.bacnet_app,
        timeout_seconds=int(s.get("timeout_seconds", 30)),
        low_limit=low_limit,
        high_limit=high_limit,
    )

    now_ts = time.time()

    # 3) Marcar vistos
    for d in devices:
        poller.mark_device_seen(
            device_instance=int(d["device_id"]),
            ip=str(d["ip"]),
            vendor_id=int(d["vendor_id"]) if d.get("vendor_id") is not None else None,
            now_ts=now_ts,
        )

    # 4) Finalizar estado offline/online
    poller.finalize_offline_status()

    return {
        "devices_seen": len(devices),
        "devices_total_known": len(poller.devices),
        "ts": now_ts,
    }