# innes_cuarto_pruebas/bacnet_gateway/discover.py

from __future__ import annotations

import asyncio
from typing import Any

from .errors import DeviceTimeoutError


async def discover_devices(
    app: Any,
    *,
    timeout_seconds: int = 30,
    low_limit=None,
    high_limit=None,
) -> list[dict[str, Any]]:
    """Ejecuta Who-Is y devuelve una lista de dispositivos vistos.

    Retorna lista de dicts:
    - ip
    - device_id
    - vendor_id

    Nota:
    - La estructura exacta de los objetos I-Am puede variar por versión de BACpypes3.
      Este parser está escrito para la intención del proyecto; se valida/ajusta en
      integración real con red BACnet.
    """

    try:
        # Who-Is (broadcast) con timeout
        i_ams = await asyncio.wait_for(app.who_is(low_limit, high_limit), timeout=timeout_seconds)

        devices: list[dict[str, Any]] = []
        for i_am in i_ams:
            # Best-effort parsing
            ip = getattr(i_am, "pduSource", None)
            vendor_id = getattr(i_am, "vendorID", None)
            dev_id = getattr(i_am, "iAmDeviceIdentifier", None)

            device_instance = None
            try:
                # iAmDeviceIdentifier suele ser tupla (objectType, instance)
                if dev_id is not None:
                    device_instance = int(dev_id[1])
            except Exception:
                device_instance = None

            devices.append(
                {
                    "ip": str(ip) if ip is not None else None,
                    "device_id": device_instance,
                    "vendor_id": int(vendor_id) if vendor_id is not None else None,
                }
            )

        # Filtramos entradas incompletas
        return [d for d in devices if d.get("device_id") is not None and d.get("ip")]

    except Exception as e:
        raise DeviceTimeoutError(f"Fallo en discovery: {e}") from e