# bacnet/history_services.py

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone

from .models import BacnetObjectPoint, BacnetPointSample


def get_last_samples(point_id: int, limit: int = 200) -> list[dict[str, Any]]:
    """Últimas N muestras de un punto."""

    qs = (
        BacnetPointSample.objects.filter(point_id=point_id)
        .order_by("-ts")[:limit]
    )

    return [
        {
            "ts": s.ts,
            "value": s.value,
            "quality": s.quality,
        }
        for s in qs
    ]


def get_samples_range(point_id: int, start: datetime, end: datetime, limit: int = 5000) -> list[dict[str, Any]]:
    """Muestras en rango [start, end]."""

    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)

    qs = (
        BacnetPointSample.objects.filter(point_id=point_id, ts__gte=start, ts__lte=end)
        .order_by("ts")[:limit]
    )

    return [
        {
            "ts": s.ts,
            "value": s.value,
            "quality": s.quality,
        }
        for s in qs
    ]


def resolve_point(device_instance: int, object_id_str: str) -> BacnetObjectPoint:
    """Helper para resolver point por device_instance + object_id_str."""

    return BacnetObjectPoint.objects.select_related("device").get(
        device__device_instance=device_instance,
        object_id_str=object_id_str,
    )