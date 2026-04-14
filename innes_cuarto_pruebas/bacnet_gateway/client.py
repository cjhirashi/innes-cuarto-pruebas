# innes_cuarto_pruebas/bacnet_gateway/client.py

from __future__ import annotations

from typing import Any

from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject
from bacpypes3.pdu import IPv4Address

from .errors import BACnetGatewayError


async def create_bacnet_application(
	*,
	bind_ip: str,
	mask: str,
	local_port: int = 47808,
	# --- Identidad BACnet del poller (requerida por bacpypes3) ---
	device_instance: int = 599,
	device_name: str = "PR_0003 Poller",
	# --- BBMD / Foreign Device (opcional) ---
	bbmd_enabled: bool = False,
	bbmd_address: str | None = None,
	foreign_device_enabled: bool = False,
	foreign_device_bbmd_address: str | None = None,
	foreign_device_ttl_seconds: int = 600,
) -> NormalApplication:
	"""Crea la aplicación BACnet/IP (BACpypes3) en bind_ip/mask.

	Notas:
	- Esta función solo se llama al arrancar el poller.
	- `NormalApplication` requiere `device_object`.
	- En tu versión instalada, el objeto de dispositivo es `DeviceObject` (no `LocalDeviceObject`).
	- `IPv4Address` no acepta el formato "IP:PORT/MASK"; se usa "IP/MASK".
	- El binding del puerto/BBMD/Foreign Device se integra en fase posterior.
	"""

	try:
		local_address = IPv4Address(f"{bind_ip}/{mask}")

		device_object = DeviceObject(
			objectIdentifier=("device", int(device_instance)),
			objectName=str(device_name),
		)

		# --- Inicialización del stack BACpypes3 ---
		app = NormalApplication(
			device_object=device_object,
			local_address=local_address,
		)

		# --- Hooks BBMD/Foreign Device (pendiente de implementación real) ---
		_ = {
			"local_port": local_port,
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