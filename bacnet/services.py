# bacnet/services.py

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from django.conf import settings as django_settings
from django.db import transaction
from django.utils import timezone

import requests
from requests import RequestException

from .models import BacnetAuditEvent, BacnetDevice, BacnetObjectPoint


# Base URL del poller (API local).
#
# Orden de resolución:
# 1) Variable de entorno BACNET_POLLER_BASE_URL
# 2) Django settings: BACNET_POLLER_BASE_URL
# 3) Default local
POLLER_BASE_URL = (
	os.getenv("BACNET_POLLER_BASE_URL")
	or getattr(django_settings, "BACNET_POLLER_BASE_URL", None)
	or "http://127.0.0.1:8001"
)


@dataclass
class DiscoveredDevice:
    """DTO de dispositivo descubierto (resultado de Who-Is/I-Am)."""

    device_instance: int
    ip: str
    vendor_id: int | None = None


@transaction.atomic
def sync_devices_inventory(discovered: list[DiscoveredDevice]) -> dict[str, Any]:
    """Upsert de inventario de dispositivos.

    Reglas:
    - Crear si no existe.
    - Si existe, actualizar ip/vendor_id.
    - Persistir last_seen_at.
    """

    created = 0
    updated = 0
    unchanged = 0

    created_device_instances: list[int] = []

    now = timezone.now()

    for d in discovered:
        obj, was_created = BacnetDevice.objects.get_or_create(
            device_instance=d.device_instance,
            defaults={
                "ip": d.ip,
                "vendor_id": d.vendor_id,
                "last_seen_at": now,
            },
        )

        if was_created:
            created += 1
            created_device_instances.append(d.device_instance)
            continue

        changed = False

        if obj.ip != d.ip:
            obj.ip = d.ip
            changed = True

        if obj.vendor_id != d.vendor_id:
            obj.vendor_id = d.vendor_id
            changed = True

        # Refrescamos last_seen_at
        if obj.last_seen_at != now:
            obj.last_seen_at = now
            changed = True

        if changed:
            obj.save(update_fields=["ip", "vendor_id", "last_seen_at", "updated_at"])
            updated += 1
        else:
            unchanged += 1

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "total": len(discovered),
        "created_device_instances": created_device_instances,
    }


def _poller_healthcheck() -> None:
    try:
        r = requests.get(f"{POLLER_BASE_URL}/health", timeout=5)
        r.raise_for_status()
    except RequestException as e:
        raise RuntimeError(f"No se pudo conectar al poller ({POLLER_BASE_URL}). ¿Está corriendo? Error: {e}")


def _fetch_discovered_devices_from_poller() -> list[DiscoveredDevice]:
    """Dispara discovery manual en el poller y obtiene la lista live."""

    _poller_healthcheck()

    try:
        r = requests.post(f"{POLLER_BASE_URL}/discover", timeout=30)
        r.raise_for_status()

        r = requests.get(f"{POLLER_BASE_URL}/devices", timeout=30)
        r.raise_for_status()
        payload = r.json()

    except RequestException as e:
        raise RuntimeError(f"No se pudo ejecutar discovery/consultar devices en el poller. Error: {e}")

    devices: list[DiscoveredDevice] = []
    for d in payload.get("devices", []):
        devices.append(
            DiscoveredDevice(
                device_instance=int(d["device_instance"]),
                ip=str(d["ip"]),
                vendor_id=int(d["vendor_id"]) if d.get("vendor_id") is not None else None,
            )
        )

    return devices


def run_scan_and_sync_inventory() -> dict[str, Any]:
    """Caso de uso: scan manual + sync inventario a DB."""

    try:
        discovered = _fetch_discovered_devices_from_poller()
        sync_result = sync_devices_inventory(discovered)

        # Nota: el mapeo de puntos se dispara manualmente por dispositivo.
        return {
            "ok": True,
            "poller_devices": len(discovered),
            "db": sync_result,
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


# -----------------------------
# Fase 3: Sync de puntos (mapeo)
# -----------------------------


@dataclass
class DiscoveredPoint:
    """DTO de punto/objeto descubierto para inventario persistente."""

    object_type: str
    object_instance: int
    object_id_str: str
    object_name: str | None = None
    description: str | None = None
    units: str | None = None


def _fetch_points_from_poller(device_instance: int) -> list[DiscoveredPoint]:
    """Obtiene inventario de puntos desde el poller.

    Contrato: GET /devices/{device_instance}/points
    """

    _poller_healthcheck()

    try:
        r = requests.get(f"{POLLER_BASE_URL}/devices/{device_instance}/points", timeout=60)
        r.raise_for_status()
        payload = r.json()

    except RequestException as e:
        raise RuntimeError(f"No se pudo obtener puntos desde el poller. Error: {e}")

    if not payload.get("ok"):
        return []

    points: list[DiscoveredPoint] = []
    for p in payload.get("points", []):
        points.append(
            DiscoveredPoint(
                object_type=str(p.get("object_type")),
                object_instance=int(p.get("object_instance")),
                object_id_str=str(p.get("object_id_str")),
                object_name=p.get("object_name"),
                description=p.get("description"),
                units=p.get("units"),
            )
        )

    return points


@transaction.atomic
def sync_device_points(device_instance: int, discovered_points: list[DiscoveredPoint]) -> dict[str, Any]:
    """Sincroniza puntos de 1 dispositivo con regla espejo 1:1.

    Reglas:
    - Upsert de puntos presentes.
    - Hard delete de puntos que ya existían en DB pero ya no aparecen.
    """

    device = BacnetDevice.objects.get(device_instance=device_instance)

    discovered_by_id = {p.object_id_str: p for p in discovered_points}
    discovered_ids = set(discovered_by_id.keys())

    existing_qs = BacnetObjectPoint.objects.filter(device=device)
    existing_by_id = {p.object_id_str: p for p in existing_qs}
    existing_ids = set(existing_by_id.keys())

    created = 0
    updated = 0

    for object_id_str, dp in discovered_by_id.items():
        obj = existing_by_id.get(object_id_str)

        if not obj:
            BacnetObjectPoint.objects.create(
                device=device,
                object_type=dp.object_type,
                object_instance=dp.object_instance,
                object_id_str=dp.object_id_str,
                object_name=dp.object_name,
                description=dp.description,
                units=dp.units,
            )
            created += 1
            continue

        changed = False
        for field, value in {
            "object_type": dp.object_type,
            "object_instance": dp.object_instance,
            "object_name": dp.object_name,
            "description": dp.description,
            "units": dp.units,
        }.items():
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed = True

        if changed:
            obj.save()
            updated += 1

    to_delete_ids = existing_ids - discovered_ids
    deleted, _ = BacnetObjectPoint.objects.filter(device=device, object_id_str__in=to_delete_ids).delete()

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "total_discovered": len(discovered_points),
    }


def run_remap_points_and_sync(device_instance: int) -> dict[str, Any]:
    """Caso de uso: remapeo manual de puntos + sync (hard delete)."""

    try:
        points = _fetch_points_from_poller(device_instance)
        result = sync_device_points(device_instance, points)

        return {"ok": True, "device_instance": device_instance, "points": result}

    except Exception as e:
        return {"ok": False, "error": str(e)}


# -----------------------------
# Fase 5: Write/Release (Pruebas web)
# -----------------------------


def write_present_value(
    *,
    device_instance: int,
    object_id_str: str,
    value: float,
    priority: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Solicita al poller escribir presentValue y hacer read-back."""

    _poller_healthcheck()

    payload = {
        "device_instance": int(device_instance),
        "object_id_str": str(object_id_str),
        "value": float(value),
        "priority": priority,
        "reason": reason,
    }

    try:
        r = requests.post(f"{POLLER_BASE_URL}/write/present-value", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()

        BacnetAuditEvent.objects.create(
            action=BacnetAuditEvent.ACTION_WRITE_PV,
            reason=reason,
            device_instance=int(device_instance),
            object_id_str=str(object_id_str),
            priority=priority,
            value=str(value),
            result="OK" if result.get("ok") else "FAIL",
            technical_message=None if result.get("ok") else str(result.get("error")),
        )

        return result

    except Exception as e:
        BacnetAuditEvent.objects.create(
            action=BacnetAuditEvent.ACTION_WRITE_PV,
            reason=reason,
            device_instance=int(device_instance),
            object_id_str=str(object_id_str),
            priority=priority,
            value=str(value),
            result="FAIL",
            technical_message=str(e),
        )
        return {"ok": False, "error": str(e)}


def release_present_value(
    *,
    device_instance: int,
    object_id_str: str,
    priority: int,
    reason: str | None = None,
) -> dict[str, Any]:
    """Solicita al poller liberar presentValue en una prioridad."""

    _poller_healthcheck()

    payload = {
        "device_instance": int(device_instance),
        "object_id_str": str(object_id_str),
        "priority": int(priority),
        "reason": reason,
    }

    try:
        r = requests.post(f"{POLLER_BASE_URL}/release/present-value", json=payload, timeout=30)
        r.raise_for_status()
        result = r.json()

        BacnetAuditEvent.objects.create(
            action=BacnetAuditEvent.ACTION_RELEASE,
            reason=reason,
            device_instance=int(device_instance),
            object_id_str=str(object_id_str),
            priority=int(priority),
            value=None,
            result="OK" if result.get("ok") else "FAIL",
            technical_message=None if result.get("ok") else str(result.get("error")),
        )

        return result

    except Exception as e:
        BacnetAuditEvent.objects.create(
            action=BacnetAuditEvent.ACTION_RELEASE,
            reason=reason,
            device_instance=int(device_instance),
            object_id_str=str(object_id_str),
            priority=int(priority),
            value=None,
            result="FAIL",
            technical_message=str(e),
        )
        return {"ok": False, "error": str(e)}


def release_present_value_all(
    *,
    device_instance: int,
    object_id_str: str,
    priority: int = 8,
    reason: str | None = None,
) -> dict[str, Any]:
    """Solicita al poller liberar prioridades 1..16 (best-effort).

    Nota:
    - El endpoint del poller requiere un payload tipo ReleasePVRequest.
      En esta llamada, priority es un valor placeholder (se ignora dentro del loop 1..16).
    """

    _poller_healthcheck()

    payload = {
        "device_instance": int(device_instance),
        "object_id_str": str(object_id_str),
        "priority": int(priority),
        "reason": reason,
    }

    try:
        r = requests.post(f"{POLLER_BASE_URL}/release-all/present-value", json=payload, timeout=60)
        r.raise_for_status()
        result = r.json()

        BacnetAuditEvent.objects.create(
            action=BacnetAuditEvent.ACTION_RELEASE_ALL,
            reason=reason,
            device_instance=int(device_instance),
            object_id_str=str(object_id_str),
            priority=None,
            value=None,
            result="OK" if result.get("ok") else "FAIL",
            technical_message=None if result.get("ok") else str(result.get("error")),
        )

        return result

    except Exception as e:
        BacnetAuditEvent.objects.create(
            action=BacnetAuditEvent.ACTION_RELEASE_ALL,
            reason=reason,
            device_instance=int(device_instance),
            object_id_str=str(object_id_str),
            priority=None,
            value=None,
            result="FAIL",
            technical_message=str(e),
        )

        return {"ok": False, "error": str(e)}