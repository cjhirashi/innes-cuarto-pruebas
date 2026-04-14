# bacnet/admin.py

# --- Imports ---
from __future__ import annotations

from django.contrib import admin

from .models import BacnetAuditEvent, BacnetDevice, BacnetObjectPoint, BacnetPointSample, BacnetSetting


@admin.register(BacnetSetting)
class BacnetSettingAdmin(admin.ModelAdmin):
    """Admin para configuración BACnet (single-row)."""

    list_display = (
        "id",
        "bind_ip",
        "mask",
        "local_port",
        "broadcast",
        "timeout_seconds",
        "retries",
        "discovery_interval_sec",
        "offline_threshold_broadcast_cycles",
        "write_priority_default",
        "bbmd_enabled",
        "foreign_device_enabled",
        "updated_at",
    )


@admin.register(BacnetDevice)
class BacnetDeviceAdmin(admin.ModelAdmin):
    """Admin de inventario de dispositivos."""

    list_display = (
        "device_instance",
        "ip",
        "vendor_id",
        "last_seen_at",
        "updated_at",
    )
    search_fields = ("device_instance", "ip")
    list_filter = ("vendor_id",)


@admin.register(BacnetObjectPoint)
class BacnetObjectPointAdmin(admin.ModelAdmin):
    """Admin de inventario de puntos."""

    list_display = (
        "device",
        "object_id_str",
        "object_type",
        "object_instance",
        "object_name",
        "units",
        "historical_enabled",
        "historical_interval_sec",
        "historical_sample_interval_sec",
        "updated_at",
    )
    search_fields = ("object_id_str", "object_name", "device__device_instance")
    list_filter = ("object_type", "units", "historical_enabled")


@admin.register(BacnetAuditEvent)
class BacnetAuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "device_instance",
        "object_id_str",
        "priority",
        "value",
        "result",
    )
    list_filter = ("action", "result")
    search_fields = ("device_instance", "object_id_str", "technical_message")


@admin.register(BacnetPointSample)
class BacnetPointSampleAdmin(admin.ModelAdmin):
    list_display = ("ts", "point", "value", "quality")
    list_filter = ("quality",)
    search_fields = ("point__object_id_str", "point__device__device_instance")