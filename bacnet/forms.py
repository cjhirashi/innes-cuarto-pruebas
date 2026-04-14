# bacnet/forms.py

# --- Imports ---
from __future__ import annotations

from django import forms

from .models import BacnetObjectPoint, BacnetSetting


class BacnetSettingForm(forms.ModelForm):
	"""Edición de parámetros BACnet/IP (single-row)."""

	class Meta:
		model = BacnetSetting
		fields = [
			"bind_ip",
			"mask",
			"local_port",
			"broadcast",
			"timeout_seconds",
			"retries",
			"discovery_interval_sec",
			"offline_threshold_broadcast_cycles",
			"write_priority_default",
		]


class BacnetObjectPointForm(forms.ModelForm):
    """Edición de configuración por punto (históricos)."""

    class Meta:
        model = BacnetObjectPoint
        fields = [
            "historical_enabled",
            "historical_interval_sec",
            "historical_sample_interval_sec",
        ]

    def clean(self):
        cleaned = super().clean()

        interval = cleaned.get("historical_interval_sec")
        sample_interval = cleaned.get("historical_sample_interval_sec")

        # --- Regla anti-config inválida ---
        # Si hay subsampling, debe ser >= intervalo de lectura del punto.
        if sample_interval is not None and interval is not None:
            if int(sample_interval) < int(interval):
                self.add_error(
                    "historical_sample_interval_sec",
                    "Debe ser mayor o igual a historical_interval_sec.",
                )

        return cleaned