# innes_cuarto_pruebas/bacnet_gateway/read_write.py

from __future__ import annotations

import asyncio
from typing import Any

from bacpypes3.primitivedata import ObjectIdentifier, Real, Null

from .errors import PropertyReadError, PropertyWriteError


async def read_present_value(
    app: Any,
    *,
    device_ip: str,
    object_id_str: str,
    timeout_seconds: int = 5,
) -> Any:
    """ReadProperty presentValue."""

    try:
        oid = ObjectIdentifier(object_id_str)
        value = await asyncio.wait_for(app.read_property(device_ip, oid, "presentValue"), timeout=timeout_seconds)
        return value
    except Exception as e:
        raise PropertyReadError(f"Error leyendo {object_id_str} en {device_ip}: {e}") from e


async def write_present_value(
    app: Any,
    *,
    device_ip: str,
    object_id_str: str,
    value: float,
    priority: int = 8,
    timeout_seconds: int = 5,
) -> None:
    """WriteProperty presentValue con prioridad."""

    try:
        oid = ObjectIdentifier(object_id_str)
        await asyncio.wait_for(
            app.write_property(device_ip, oid, "presentValue", Real(value), priority=int(priority)),
            timeout=timeout_seconds,
        )
    except Exception as e:
        raise PropertyWriteError(f"Error escribiendo {object_id_str} en {device_ip}: {e}") from e


async def release_present_value(
    app: Any,
    *,
    device_ip: str,
    object_id_str: str,
    priority: int,
    timeout_seconds: int = 5,
) -> None:
    """Release presentValue (escritura de Null) a una prioridad."""

    try:
        oid = ObjectIdentifier(object_id_str)
        await asyncio.wait_for(
            app.write_property(device_ip, oid, "presentValue", Null(), priority=int(priority)),
            timeout=timeout_seconds,
        )
    except Exception as e:
        raise PropertyWriteError(f"Error liberando {object_id_str} en {device_ip}: {e}") from e