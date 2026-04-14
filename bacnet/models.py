# bacnet/models.py

# --- Imports ---
from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class BacnetSetting(models.Model):
    """Configuración BACnet (single-row) persistida en BD.

    Regla:
    - Debe existir 1 registro activo. La UI/Admin debe impedir crear múltiples.
    """

    # --- Binding / red ---
    bind_ip = models.CharField(max_length=64)
    mask = models.CharField(max_length=8, default="24")
    local_port = models.PositiveIntegerField(
        default=47808,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
    )
    broadcast = models.CharField(max_length=64, default="*:*")

    # --- Robustez ---
    timeout_seconds = models.FloatField(default=3)
    retries = models.PositiveIntegerField(default=2)

    # --- Discovery / monitoreo ---
    discovery_interval_sec = models.PositiveIntegerField(default=30)
    offline_threshold_broadcast_cycles = models.PositiveIntegerField(default=2)

    # --- Escritura ---
    write_priority_default = models.PositiveIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="Regla: 1..8 (no usar prioridad 9).",
    )

    # --- BBMD / Foreign Device (opcional) ---
    bbmd_enabled = models.BooleanField(default=False)
    bbmd_address = models.CharField(max_length=64, blank=True, null=True)

    foreign_device_enabled = models.BooleanField(default=False)
    foreign_device_bbmd_address = models.CharField(max_length=64, blank=True, null=True)
    foreign_device_ttl_seconds = models.PositiveIntegerField(default=600)

    # --- Auditoría ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return "BacnetSetting"


class BacnetDevice(models.Model):
    """Inventario persistente de dispositivos BACnet descubiertos."""

    device_instance = models.PositiveIntegerField(unique=True)

    # Última IP conocida (a partir de I-Am / source)
    ip = models.CharField(max_length=64)

    # Metadata opcional
    vendor_id = models.PositiveIntegerField(blank=True, null=True)
    vendor_name = models.CharField(max_length=128, blank=True, null=True)
    model_name = models.CharField(max_length=128, blank=True, null=True)
    firmware = models.CharField(max_length=128, blank=True, null=True)

    # Marca de tiempo (persistente) del último descubrimiento
    last_seen_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["device_instance"]

    def __str__(self) -> str:
        return f"Device {self.device_instance}"


class BacnetObjectPoint(models.Model):
    """Inventario persistente de puntos/objetos BACnet por dispositivo.

    Regla de unicidad:
    - Un punto es único por (device, object_id_str).
    """

    device = models.ForeignKey(BacnetDevice, on_delete=models.CASCADE, related_name="points")

    # Identificadores
    object_type = models.CharField(max_length=64)  # ej: analogInput
    object_instance = models.PositiveIntegerField()
    object_id_str = models.CharField(max_length=64)  # ej: analogInput:3

    # Metadata
    object_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    units = models.CharField(max_length=64, blank=True, null=True)

    # Históricos (Fase 6)
    historical_enabled = models.BooleanField(default=False)

    # Intervalo de lectura del punto (segundos) para polling/buffer
    historical_interval_sec = models.PositiveIntegerField(default=5)

    # Subsampling del histórico: intervalo mínimo entre registros persistidos.
    # Regla: debe ser >= historical_interval_sec.
    historical_sample_interval_sec = models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["device", "object_id_str"], name="uniq_point_per_device"),
        ]
        ordering = ["device", "object_type", "object_instance"]

    def __str__(self) -> str:
        return f"{self.device.device_instance}::{self.object_id_str}"


class BacnetAuditEvent(models.Model):
    """Auditoría mínima de acciones BACnet (MVP).

    En Fase 5 se usa principalmente para WRITE_PV.
    """

    ACTION_SCAN = "SCAN"
    ACTION_READ_PV = "READ_PV"
    ACTION_WRITE_PV = "WRITE_PV"
    ACTION_RELEASE = "RELEASE"
    ACTION_RELEASE_ALL = "RELEASE_ALL"

    ACTION_CHOICES = [
        (ACTION_SCAN, "SCAN"),
        (ACTION_READ_PV, "READ_PV"),
        (ACTION_WRITE_PV, "WRITE_PV"),
        (ACTION_RELEASE, "RELEASE"),
        (ACTION_RELEASE_ALL, "RELEASE_ALL"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)

    # user: se deja nullable para permitir acciones del poller sin request Django
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)

    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True, null=True)

    device_instance = models.PositiveIntegerField()
    object_id_str = models.CharField(max_length=64)

    priority = models.PositiveIntegerField(blank=True, null=True)
    value = models.CharField(max_length=128, blank=True, null=True)

    result = models.CharField(max_length=16, default="OK")  # OK/FAIL
    technical_message = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.created_at} {self.action} {self.device_instance} {self.object_id_str}"


class BacnetPointSample(models.Model):
    """Muestra histórica persistente (opcional) de un punto."""

    point = models.ForeignKey(BacnetObjectPoint, on_delete=models.CASCADE, related_name="samples")
    ts = models.DateTimeField()

    # Guardamos como texto para flexibilidad (float/bool/int); se normaliza en UI
    value = models.CharField(max_length=128, blank=True, null=True)
    quality = models.CharField(max_length=32, default="OK")  # OK/OFFLINE/ERROR

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["point", "ts"]),
        ]
        ordering = ["-ts"]

    def __str__(self) -> str:
        return f"{self.point.object_id_str} {self.ts} {self.value}"