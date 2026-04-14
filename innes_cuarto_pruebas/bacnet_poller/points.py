# innes_cuarto_pruebas/bacnet_poller/points.py

from __future__ import annotations

from typing import Any

from bacpypes3.primitivedata import ObjectIdentifier


async def enumerate_device_points(
    app: Any,
    *,
    device_ip: str,
    device_instance: int,
) -> list[dict[str, Any]]:
    """Enumera puntos del dispositivo leyendo objectList y metadatos básicos."""

    device_obj = ObjectIdentifier(f"device:{int(device_instance)}")
    obj_list = await app.read_property(device_ip, device_obj, "objectList")

    points: list[dict[str, Any]] = []

    for obj_id in obj_list:
        try:
            oid = obj_id if isinstance(obj_id, ObjectIdentifier) else ObjectIdentifier(obj_id)

            object_type = str(oid[0])
            object_instance = int(oid[1])
            object_id_str = f"{object_type}:{object_instance}"

            # Metadatos (best-effort)
            object_name = None
            description = None
            units = None

            try:
                object_name = await app.read_property(device_ip, oid, "objectName")
            except Exception:
                pass

            try:
                description = await app.read_property(device_ip, oid, "description")
            except Exception:
                pass

            try:
                units = await app.read_property(device_ip, oid, "units")
            except Exception:
                pass

            points.append(
                {
                    "object_type": object_type,
                    "object_instance": object_instance,
                    "object_id_str": object_id_str,
                    "object_name": str(object_name) if object_name is not None else None,
                    "description": str(description) if description is not None else None,
                    "units": str(units) if units is not None else None,
                }
            )

        except Exception:
            continue

    return points