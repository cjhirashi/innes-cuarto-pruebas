# innes_cuarto_pruebas/bacnet_poller/reload.py

from __future__ import annotations

from typing import Any

from .app import PollerApp


def replace_poll_targets(poller: PollerApp, *, targets: list[dict[str, Any]]) -> dict[str, Any]:
    """Reemplaza poll_targets desde una lista plana.

    targets: [{"device_instance": 123, "object_id_str": "analogValue:3"}, ...]
    """

    poller.poll_targets = {}

    for t in targets:
        di = int(t["device_instance"])
        oid = str(t["object_id_str"])
        poller.poll_targets.setdefault(di, []).append(oid)

    return {
        "ok": True,
        "devices": len(poller.poll_targets),
        "points": sum(len(v) for v in poller.poll_targets.values()),
    }