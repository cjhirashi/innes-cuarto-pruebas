# bacnet/tests.py

# --- Imports ---
from __future__ import annotations

from django.test import TestCase

from .forms import BacnetObjectPointForm
from .models import BacnetDevice, BacnetObjectPoint


class BacnetObjectPointFormTests(TestCase):
    """Tests mínimos para validar configuración de históricos por punto."""

    def setUp(self):
        # --- Dispositivo dummy ---
        self.device = BacnetDevice.objects.create(
            device_instance=1,
            ip="127.0.0.1",
            vendor_id=999,
        )

        # --- Punto dummy ---
        self.point = BacnetObjectPoint.objects.create(
            device=self.device,
            object_type="analogInput",
            object_instance=1,
            object_id_str="analogInput:1",
            object_name="Test Point",
            description=None,
            units=None,
            historical_enabled=False,
            historical_interval_sec=5,
        )

    def test_sample_interval_must_be_greater_or_equal_than_interval(self):
        """No permitir sample < interval."""

        form = BacnetObjectPointForm(
            data={
                "historical_enabled": True,
                "historical_interval_sec": 10,
                "historical_sample_interval_sec": 5,
            },
            instance=self.point,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("historical_sample_interval_sec", form.errors)

    def test_sample_interval_equal_is_allowed(self):
        """Permitir sample == interval."""

        form = BacnetObjectPointForm(
            data={
                "historical_enabled": True,
                "historical_interval_sec": 10,
                "historical_sample_interval_sec": 10,
            },
            instance=self.point,
        )

        self.assertTrue(form.is_valid())

    def test_sample_interval_null_is_allowed(self):
        """Permitir sample = NULL (usa intervalo base)."""

        form = BacnetObjectPointForm(
            data={
                "historical_enabled": True,
                "historical_interval_sec": 10,
                "historical_sample_interval_sec": "",
            },
            instance=self.point,
        )

        self.assertTrue(form.is_valid())