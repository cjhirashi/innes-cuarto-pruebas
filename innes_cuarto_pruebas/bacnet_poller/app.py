# innes_cuarto_pruebas/bacnet_poller/app.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceLiveState:
    """Estado en vivo (no persistente) de un dispositivo BACnet descubierto."""

    device_instance: int
    ip: str

    vendor_id: int | None = None

    last_seen_ts: float | None = None
    offline_cycles: int = 0
    online: bool = True


@dataclass
class PollerApp:
    """Contenedor principal del poller (estado en memoria)."""

    # Settings efectivos (dict plano) provistos por main.py
    settings: dict[str, Any]

    # --- Socket dueño único ---
    # Instancia BACpypes3 NormalApplication (creada una vez al arrancar el poller)
    bacnet_app: Any

    # --- Stores en memoria ---
    devices: dict[int, DeviceLiveState] = field(default_factory=dict)

    # device_instance -> list[object_id_str]
    poll_targets: dict[int, list[str]] = field(default_factory=dict)

    # device_instance -> object_id_str -> PointBuffer (definido en polling.py)
    point_buffers: dict[int, dict[str, Any]] = field(default_factory=dict)

    # --- Helpers de estado ---
    def mark_device_seen(self, device_instance: int, ip: str, vendor_id: int | None, now_ts: float) -> None:
        state = self.devices.get(device_instance)
        if not state:
            self.devices[device_instance] = DeviceLiveState(
                device_instance=int(device_instance),
                ip=str(ip),
                vendor_id=vendor_id,
                last_seen_ts=now_ts,
                offline_cycles=0,
                online=True,
            )
            return

        state.ip = str(ip)
        state.vendor_id = vendor_id
        state.last_seen_ts = now_ts
        state.offline_cycles = 0
        state.online = True

    def mark_all_devices_offline_cycle_increment(self) -> None:
        for state in self.devices.values():
            state.offline_cycles += 1

    def finalize_offline_status(self) -> None:
        threshold = int(self.settings.get("offline_threshold_broadcast_cycles", 2))
        for state in self.devices.values():
            state.online = state.offline_cycles < threshold