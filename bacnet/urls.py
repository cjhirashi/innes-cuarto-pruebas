# bacnet/urls.py

# --- Imports ---
from __future__ import annotations

from django.urls import path

from . import views


app_name = "bacnet"

urlpatterns = [
    # --- Scan / Discovery ---
    path("scan/", views.scan_page, name="scan"),
    path("scan/run/", views.scan_run, name="scan_run"),

    # --- Mapeo / remapeo de puntos ---
    path("devices/<int:device_instance>/remap/", views.device_remap_points, name="device_remap_points"),

    # --- Detalle dispositivo (UI mínima para remap) ---
    path("devices/<int:device_instance>/", views.device_detail, name="device_detail"),

	# --- Históricos (Fase 6) ---
	path(
		"devices/<int:device_instance>/points/<str:object_id_str>/history/",
		views.point_history_settings_page,
		name="point_history_settings_page",
	),
	path(
		"devices/<int:device_instance>/points/<str:object_id_str>/history/save/",
		views.point_history_settings_save,
		name="point_history_settings_save",
	),

    # --- Escritura (MVP) ---
    path(
        "devices/<int:device_instance>/points/<str:object_id_str>/write/",
        views.point_write_present_value,
        name="point_write_present_value",
    ),

    path(
        "devices/<int:device_instance>/points/<str:object_id_str>/release/",
        views.point_release_present_value,
        name="point_release_present_value",
    ),
    path(
        "devices/<int:device_instance>/points/<str:object_id_str>/release-all/",
        views.point_release_present_value_all,
        name="point_release_present_value_all",
    ),

	# --- Settings ---
	path("settings/", views.settings_page, name="settings"),
	path("settings/save/", views.settings_save, name="settings_save"),

	# --- Inventory ---
	path("inventory/", views.inventory_page, name="inventory"),

	# --- Tests ---
	path("tests/", views.tests_page, name="tests"),

	# --- Audit ---
	path("audit/", views.audit_page, name="audit"),
]