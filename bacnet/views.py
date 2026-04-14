# bacnet/views.py

# --- Imports ---
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import BacnetObjectPointForm, BacnetSettingForm
from .models import BacnetDevice, BacnetSetting
from .services import (
	release_present_value,
	release_present_value_all,
	run_remap_points_and_sync,
	run_scan_and_sync_inventory,
	write_present_value,
)


# -----------------------------------------------------------------------------
# Scan
# -----------------------------------------------------------------------------
@require_GET
def scan_page(request: HttpRequest) -> HttpResponse:
	"""Página de escaneo BACnet (MVP)."""

	# --- Inventario actual (persistente) ---
	devices = BacnetDevice.objects.all().order_by("device_instance")

	# --- Resultado de último scan (session) ---
	last_result = request.session.get("bacnet_scan_last_result")

	# --- Resultado de último remapeo (session) ---
	last_remap_result = request.session.get("bacnet_remap_last_result")

	ctx = {
		"devices": devices,
		"last_result": last_result,
		"last_remap_result": last_remap_result,
	}

	return render(request, "bacnet/scan.html", ctx)


@require_POST
def scan_run(request: HttpRequest) -> HttpResponse:
	"""Ejecuta discovery manual en el poller y sincroniza inventario a BD."""

	result = run_scan_and_sync_inventory()

	# Guardamos resultado en session para mostrarlo al volver a la página
	request.session["bacnet_scan_last_result"] = result

	return redirect(reverse("bacnet:scan"))


# -----------------------------------------------------------------------------
# Device detail
# -----------------------------------------------------------------------------
@require_POST
def device_remap_points(request: HttpRequest, device_instance: int) -> HttpResponse:
	"""Botón manual: remap de puntos del dispositivo (hard delete)."""

	result = run_remap_points_and_sync(device_instance=device_instance)
	request.session["bacnet_remap_last_result"] = result

	# Por ahora regresamos al detalle
	return redirect(reverse("bacnet:device_detail", kwargs={"device_instance": device_instance}))


@require_GET
def device_detail(request: HttpRequest, device_instance: int) -> HttpResponse:
	"""Detalle mínimo de dispositivo + puntos (inventario persistente)."""

	device = BacnetDevice.objects.get(device_instance=device_instance)
	points = device.points.all().order_by("object_type", "object_instance")

	last_remap_result = request.session.get("bacnet_remap_last_result")
	last_write_result = request.session.get("bacnet_write_last_result")
	last_release_result = request.session.get("bacnet_release_last_result")
	last_release_all_result = request.session.get("bacnet_release_all_last_result")

	ctx = {
		"device": device,
		"points": points,
		"last_remap_result": last_remap_result,
		"last_write_result": last_write_result,
		"last_release_result": last_release_result,
		"last_release_all_result": last_release_all_result,
	}

	return render(request, "bacnet/device_detail.html", ctx)


# -----------------------------------------------------------------------------
# Point history settings (Fase 6)
# -----------------------------------------------------------------------------
@require_GET
def point_history_settings_page(
	request: HttpRequest,
	device_instance: int,
	object_id_str: str,
) -> HttpResponse:
	"""Página de ajustes de histórico por punto."""

	point = BacnetDevice.objects.get(device_instance=device_instance).points.get(object_id_str=object_id_str)
	form = BacnetObjectPointForm(instance=point)

	ctx = {
		"device": point.device,
		"point": point,
		"form": form,
	}
	return render(request, "bacnet/point_history_settings.html", ctx)


@require_POST
def point_history_settings_save(
	request: HttpRequest,
	device_instance: int,
	object_id_str: str,
) -> HttpResponse:
	"""Guarda ajustes de histórico por punto (Fase 6)."""

	point = BacnetDevice.objects.get(device_instance=device_instance).points.get(object_id_str=object_id_str)
	form = BacnetObjectPointForm(request.POST, instance=point)

	if form.is_valid():
		form.save()
		return redirect(reverse("bacnet:device_detail", kwargs={"device_instance": device_instance}))

	ctx = {
		"device": point.device,
		"point": point,
		"form": form,
	}
	return render(request, "bacnet/point_history_settings.html", ctx)


# -----------------------------------------------------------------------------
# Write / Release (MVP)
# -----------------------------------------------------------------------------
@require_POST
def point_write_present_value(request: HttpRequest, device_instance: int, object_id_str: str) -> HttpResponse:
	"""Escritura MVP: presentValue (write-through) + auditoría."""

	# Payload desde form
	value_raw = request.POST.get("value")
	priority_raw = request.POST.get("priority")
	reason = request.POST.get("reason")

	try:
		value = float(value_raw) if value_raw is not None else None
	except Exception:
		value = None

	try:
		priority = int(priority_raw) if priority_raw else None
	except Exception:
		priority = None

	result = write_present_value(
		device_instance=device_instance,
		object_id_str=object_id_str,
		value=value if value is not None else 0.0,
		priority=priority,
		reason=reason,
	)

	request.session["bacnet_write_last_result"] = result

	return redirect(reverse("bacnet:device_detail", kwargs={"device_instance": device_instance}))


@require_POST
def point_release_present_value(request: HttpRequest, device_instance: int, object_id_str: str) -> HttpResponse:
	"""Release MVP: libera una prioridad específica."""

	priority_raw = request.POST.get("priority")
	reason = request.POST.get("reason")

	try:
		priority = int(priority_raw) if priority_raw else 8
	except Exception:
		priority = 8

	result = release_present_value(
		device_instance=device_instance,
		object_id_str=object_id_str,
		priority=priority,
		reason=reason,
	)

	request.session["bacnet_release_last_result"] = result
	return redirect(reverse("bacnet:device_detail", kwargs={"device_instance": device_instance}))


@require_POST
def point_release_present_value_all(request: HttpRequest, device_instance: int, object_id_str: str) -> HttpResponse:
	"""Release-all MVP: intenta liberar prioridades 1..16."""

	reason = request.POST.get("reason")
	result = release_present_value_all(
		device_instance=device_instance,
		object_id_str=object_id_str,
		reason=reason,
	)

	request.session["bacnet_release_all_last_result"] = result
	return redirect(reverse("bacnet:device_detail", kwargs={"device_instance": device_instance}))


# -----------------------------------------------------------------------------
# Settings
# -----------------------------------------------------------------------------
@require_GET
def settings_page(request: HttpRequest) -> HttpResponse:
	"""Pantalla de ajustes BACnet (single-row)."""

	setting, _created = BacnetSetting.objects.get_or_create(id=1)
	form = BacnetSettingForm(instance=setting)

	ctx = {
		"form": form,
		"saved_ok": request.session.pop("bacnet_settings_saved_ok", False),
		"message": request.session.pop("bacnet_settings_message", None),
	}
	return render(request, "bacnet/settings.html", ctx)


@require_POST
def settings_save(request: HttpRequest) -> HttpResponse:
	"""Guarda ajustes BACnet (single-row)."""

	setting, _created = BacnetSetting.objects.get_or_create(id=1)
	form = BacnetSettingForm(request.POST, instance=setting)

	if form.is_valid():
		form.save()
		request.session["bacnet_settings_saved_ok"] = True
		return redirect(reverse("bacnet:settings"))

	ctx = {
		"form": form,
		"saved_ok": False,
		"message": "Formulario inválido. Revisa los campos.",
	}
	return render(request, "bacnet/settings.html", ctx)


# -----------------------------------------------------------------------------
# Inventory
# -----------------------------------------------------------------------------
@require_GET
def inventory_page(request: HttpRequest) -> HttpResponse:
	"""Listado de inventario (dispositivos persistidos)."""

	q = (request.GET.get("q") or "").strip()
	qs = BacnetDevice.objects.all().order_by("device_instance")

	# Filtro simple (device_instance exacto por ahora; IP parcial)
	if q:
		# Intentar como int
		try:
			device_instance = int(q)
			qs = qs.filter(device_instance=device_instance)
		except Exception:
			qs = qs.filter(ip__icontains=q)

	devices = qs

	counts = {
		"devices": devices.count(),
		"points": sum(d.points.count() for d in devices),
	}

	ctx = {
		"devices": devices,
		"q": q,
		"counts": counts,
	}
	return render(request, "bacnet/inventory.html", ctx)


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------
@require_GET
def tests_page(request: HttpRequest) -> HttpResponse:
	"""Pantalla de pruebas (write/release) por punto seleccionado."""

	device_instance_raw = request.GET.get("device_instance")
	object_id_str = (request.GET.get("object_id_str") or "").strip() or None

	device_instance = None
	try:
		device_instance = int(device_instance_raw) if device_instance_raw else None
	except Exception:
		device_instance = None

	ctx = {
		"device_instance": device_instance,
		"object_id_str": object_id_str,
		"last_write_result": request.session.get("bacnet_write_last_result"),
		"last_release_result": request.session.get("bacnet_release_last_result"),
		"last_release_all_result": request.session.get("bacnet_release_all_last_result"),
	}
	return render(request, "bacnet/tests.html", ctx)


# -----------------------------------------------------------------------------
# Audit
# -----------------------------------------------------------------------------
@require_GET
def audit_page(request: HttpRequest) -> HttpResponse:
	"""Pantalla de auditoría (pendiente de conectar modelo BacnetAuditEvent)."""

	# NOTA: el modelo BacnetAuditEvent no está cargado en este archivo.
	# Cuando exista/esté listo, aquí se consultará y se pasará a template.
	ctx = {
		"events": [],
		"action": (request.GET.get("action") or "").strip() or None,
	}
	return render(request, "bacnet/audit.html", ctx)