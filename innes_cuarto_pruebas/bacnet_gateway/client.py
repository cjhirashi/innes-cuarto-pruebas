# innes_cuarto_pruebas/bacnet_gateway/client.py

from __future__ import annotations

from typing import Any

from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.pdu import IPv4Address

from .errors import BACnetGatewayError


async def create_bacnet_application(
    *,
    bind_ip: str,
    mask: str,
    local_port: int = 47808,
    # --- BBMD / Foreign Device (opcional) ---
    bbmd_enabled: bool = False,
    bbmd_address: str | None = None,
    foreign_device_enabled: bool = False,
    foreign_device_bbmd_address: str | None = None,
    foreign_device_ttl_seconds: int = 600,
) -> NormalApplication:
    """Crea la aplicación BACnet/IP (BACpypes3) en bind_ip:local_port/mask.

    Notas:
    - Esta función solo se llama al arrancar el poller.
    - La integración BBMD/Foreign Device se implementa en fase posterior.
    """

    try:
        local_address = IPv4Address(f"{bind_ip}:{int(local_port)}/{mask}")

        # --- Inicialización del stack BACpypes3 ---
        app = NormalApplication(local_address=local_address)

        # --- Hooks BBMD/Foreign Device (pendiente de implementación real) ---
        _ = {
            "bbmd_enabled": bbmd_enabled,
            "bbmd_address": bbmd_address,
            "foreign_device_enabled": foreign_device_enabled,
            "foreign_device_bbmd_address": foreign_device_bbmd_address,
            "foreign_device_ttl_seconds": foreign_device_ttl_seconds,
        }

        return app

    except Exception as e:
        raise BACnetGatewayError(f"Error al iniciar BACnet stack: {e}") from e


async def close_bacnet_application(app: Any) -> None:
    """Cierra la aplicación BACnet/IP (libera socket).

    Se llama al apagar el poller (best-effort).
    """

    try:
        if app is not None and hasattr(app, "close"):
            app.close()
    except Exception:
        # Best-effort: no reventar shutdown
        return