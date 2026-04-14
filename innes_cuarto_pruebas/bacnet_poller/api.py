# innes_cuarto_pruebas/bacnet_poller/api.py

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from innes_cuarto_pruebas.bacnet_gateway.read_write import (
    read_present_value,
    write_present_value,
    release_present_value,
)

from .app import PollerApp
from .discovery import run_discovery_once
from .polling import poll_once
from .points import enumerate_device_points


logger = logging.getLogger("bacnet_poller")


def _get_poll_targets_snapshot(poller: PollerApp) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for device_instance, object_ids in poller.poll_targets.items():
        snapshot[str(device_instance)] = list(object_ids)
    return snapshot


def _count_targets(poller: PollerApp) -> int:
    return sum(len(v) for v in poller.poll_targets.values())


def _enforce_target_limit(poller: PollerApp, *, max_points: int = 300) -> None:
    total = _count_targets(poller)
    if total > int(max_points):
        raise ValueError(f"poll_targets excede límite max_points={max_points} total={total}")


def create_api(poller: PollerApp) -> FastAPI:
    app = FastAPI(title="PR_0003 bacnet-poller", version="0.3")

    # -------------------------
    # Models
    # -------------------------

    class TargetItem(BaseModel):
        device_instance: int
        object_id_str: str = Field(..., description="Ej: analogValue:3")

    class ReplaceTargetsRequest(BaseModel):
        targets: list[TargetItem]
        max_points: int = 300

    class AppendTargetsRequest(BaseModel):
        targets: list[TargetItem]
        max_points: int = 300

    class RemoveTargetsRequest(BaseModel):
        targets: list[TargetItem]

    class WritePVRequest(BaseModel):
        device_instance: int
        object_id_str: str
        value: float
        priority: int | None = Field(None, ge=1, le=8)
        reason: str | None = None

    class ReleasePVRequest(BaseModel):
        device_instance: int
        object_id_str: str
        priority: int = Field(..., ge=1, le=16)
        reason: str | None = None

    # -------------------------
    # Endpoints
    # -------------------------

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/discover")
    async def discover():
        t0 = time.perf_counter()
        summary = await run_discovery_once(poller)
        dt_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("discover ok dt_ms=%s summary=%s", dt_ms, summary)
        return {"ok": True, "summary": summary}

    @app.get("/devices")
    async def list_devices():
        return {
            "devices": [
                {
                    "device_instance": d.device_instance,
                    "ip": d.ip,
                    "vendor_id": d.vendor_id,
                    "online": d.online,
                    "offline_cycles": d.offline_cycles,
                    "last_seen_ts": d.last_seen_ts,
                }
                for d in poller.devices.values()
            ]
        }

    @app.get("/devices/{device_instance}/points")
    async def list_device_points(device_instance: int):
        """Enumeración best-effort de puntos (para remapeo/inventario)."""

        state = poller.devices.get(int(device_instance))
        if not state:
            return {"ok": False, "error": "device_instance no encontrado en sesión", "device_instance": int(device_instance), "points": []}

        points = await enumerate_device_points(
            poller.bacnet_app,
            device_ip=str(state.ip),
            device_instance=int(device_instance),
        )

        return {"ok": True, "device_instance": int(device_instance), "points": points}

    @app.get("/devices/{device_instance}/buffers")
    async def list_device_buffers(device_instance: int):
        device_buffers = poller.point_buffers.get(int(device_instance), {})
        return {"ok": True, "device_instance": int(device_instance), "buffers": list(device_buffers.keys())}

    @app.get("/devices/{device_instance}/points/{object_id_str}/buffer")
    async def get_point_buffer(device_instance: int, object_id_str: str):
        device_buffers = poller.point_buffers.get(int(device_instance), {})
        buf = device_buffers.get(str(object_id_str))

        if not buf:
            return {"ok": False, "error": "buffer no encontrado", "device_instance": int(device_instance), "object_id_str": str(object_id_str)}

        return {
            "ok": True,
            "device_instance": int(device_instance),
            "object_id_str": str(object_id_str),
            "online": getattr(buf, "online", True),
            "last_value": getattr(buf, "last_value", None),
            "values": list(getattr(buf, "values", [])),
        }

    @app.get("/poll/targets")
    async def get_poll_targets():
        return {
            "ok": True,
            "max_points": int(poller.settings.get("max_points", 300)),
            "total_points": _count_targets(poller),
            "targets": _get_poll_targets_snapshot(poller),
        }

    @app.post("/poll/targets")
    async def replace_poll_targets(req: ReplaceTargetsRequest):
        """Reemplaza poll_targets completamente."""

        poller.poll_targets = {}
        for t in req.targets:
            poller.poll_targets.setdefault(int(t.device_instance), []).append(str(t.object_id_str))

        max_points = int(req.max_points)
        _enforce_target_limit(poller, max_points=max_points)
        poller.settings["max_points"] = max_points

        return {"ok": True, "total_points": _count_targets(poller)}

    @app.post("/poll/targets/append")
    async def append_poll_targets(req: AppendTargetsRequest):
        """Agrega targets (idempotente best-effort)."""

        for t in req.targets:
            di = int(t.device_instance)
            oid = str(t.object_id_str)
            cur = poller.poll_targets.setdefault(di, [])
            if oid not in cur:
                cur.append(oid)

        max_points = int(req.max_points)
        _enforce_target_limit(poller, max_points=max_points)
        poller.settings["max_points"] = max_points

        return {"ok": True, "total_points": _count_targets(poller)}

    @app.post("/poll/targets/remove")
    async def remove_poll_targets(req: RemoveTargetsRequest):
        """Remueve targets si existen."""

        for t in req.targets:
            di = int(t.device_instance)
            oid = str(t.object_id_str)
            cur = poller.poll_targets.get(di, [])
            if oid in cur:
                cur.remove(oid)
            if di in poller.poll_targets and not poller.poll_targets[di]:
                poller.poll_targets.pop(di, None)

        return {"ok": True, "total_points": _count_targets(poller)}

    @app.post("/write/present-value")
    async def write_pv(req: WritePVRequest):
        """Write-through: write + read-back + actualización inmediata del buffer."""

        state = poller.devices.get(int(req.device_instance))
        if not state:
            return {"ok": False, "error": "device_instance no encontrado en sesión"}
        if not state.online:
            return {"ok": False, "error": "dispositivo offline"}

        s = poller.settings
        priority = int(req.priority) if req.priority is not None else int(s.get("write_priority_default", 8))

        t0 = time.perf_counter()
        try:
            await write_present_value(
                poller.bacnet_app,
                device_ip=state.ip,
                object_id_str=str(req.object_id_str),
                value=float(req.value),
                priority=priority,
                timeout_seconds=int(s.get("timeout_seconds", 5)),
            )

            read_back = await read_present_value(
                poller.bacnet_app,
                device_ip=state.ip,
                object_id_str=str(req.object_id_str),
                timeout_seconds=int(s.get("timeout_seconds", 5)),
            )

            await poll_once(poller, device_instance=int(req.device_instance), object_id_str=str(req.object_id_str))

            dt_ms = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "write_pv ok dt_ms=%s device=%s point=%s priority=%s requested=%s read_back=%s",
                dt_ms,
                req.device_instance,
                req.object_id_str,
                priority,
                req.value,
                read_back,
            )

            return {
                "ok": True,
                "device_instance": int(req.device_instance),
                "object_id_str": str(req.object_id_str),
                "priority": priority,
                "requested": req.value,
                "read_back": read_back,
            }

        except Exception as e:
            dt_ms = int((time.perf_counter() - t0) * 1000)
            logger.exception(
                "write_pv fail dt_ms=%s device=%s point=%s error=%s",
                dt_ms,
                req.device_instance,
                req.object_id_str,
                str(e),
            )
            return {"ok": False, "error": str(e)}

    @app.post("/release/present-value")
    async def release_pv(req: ReleasePVRequest):
        state = poller.devices.get(int(req.device_instance))
        if not state:
            return {"ok": False, "error": "device_instance no encontrado en sesión"}

        s = poller.settings

        try:
            await release_present_value(
                poller.bacnet_app,
                device_ip=state.ip,
                object_id_str=str(req.object_id_str),
                priority=int(req.priority),
                timeout_seconds=int(s.get("timeout_seconds", 5)),
            )
            await poll_once(poller, device_instance=int(req.device_instance), object_id_str=str(req.object_id_str))
            return {"ok": True, "device_instance": int(req.device_instance), "object_id_str": str(req.object_id_str), "priority": int(req.priority)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.post("/release-all/present-value")
    async def release_pv_all(req: ReleasePVRequest):
        """Release all: intenta liberar prioridades 1..16 (best-effort)."""

        state = poller.devices.get(int(req.device_instance))
        if not state:
            return {"ok": False, "error": "device_instance no encontrado en sesión"}

        s = poller.settings

        ok_list: list[int] = []
        fail_list: list[dict[str, Any]] = []

        for prio in range(1, 17):
            try:
                await release_present_value(
                    poller.bacnet_app,
                    device_ip=state.ip,
                    object_id_str=str(req.object_id_str),
                    priority=int(prio),
                    timeout_seconds=int(s.get("timeout_seconds", 5)),
                )
                ok_list.append(prio)
            except Exception as e:
                fail_list.append({"priority": prio, "error": str(e)})

        await poll_once(poller, device_instance=int(req.device_instance), object_id_str=str(req.object_id_str))

        return {
            "ok": True,
            "device_instance": int(req.device_instance),
            "object_id_str": str(req.object_id_str),
            "ok_priorities": ok_list,
            "failures": fail_list,
        }

    return app