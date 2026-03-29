# INNES — Cuarto de Pruebas (PR_0003)

Plataforma web (Django) para operar un sistema de pruebas BACnet/IP que controla ~15 cajas VAV, ejecutar corridas de medición de caudales y, con esas lecturas, calcular y reportar la eficiencia de difusores de aire.

## Alcance (MVP)
- Integración BACnet/IP (gateway, discovery/scan, lectura y escritura controlada)
- Inventario persistente (sistemas, controladores/devices, objetos/variables)
- Ejecución de pruebas (TestRuns) + captura de mediciones
- Reportes HTML por prueba
- Roles: Admin / Operador / Viewer

## Arquitectura (alto nivel)
- Framework: Django (apps server-rendered con templates)
- Apps en raíz del repo:
  - core/: Home + layout global + healthcheck + utilidades
  - accounts/: autenticación + roles/permisos
  - bacnet/: gateway BAC0 + UI admin BACnet
  - inventory/: modelos y navegación de inventario BACnet
  - trials/: ejecución de pruebas y captura de mediciones
  - reports/: cálculos + render de reportes HTML
- Templates:
  - Globales: templates/
    - Layout: templates/base_layout.html
    - Componentes globales: templates/components/
  - Locales por app: [app]/templates/[app]/...
  - Componentes locales: [app]/templates/components/
- Statics globales:
  - statics/css/styles.css

## Requisitos
- Python 3.13
- Pipenv

## Configuración local (Pipenv)

### 1. Clonar y entrar
```bash
git clone https://github.com/cjhirashi/innes-cuarto-pruebas.git
```

### 2. Crear entorno e instalar dependencias
```bash
pipenv install
pipenv shell
```

### 3. Migraciones
```bash
python manage.py migrate
```

### 4. Crear superusuario
```bash
python manage.py createsuperuser
```

### 5. Levantar servidor
```bash
- python manage.py runserver
```

Abrir de forma local:
* [Home](http://127.0.0.1:8000/)
* [Admin](http://127.0.0.1:8000/admin/)

## Ejecutar en red local (LAN)
Para que otras PCs accedan desde la misma red:
```bash
python manage.py runserver 0.0.0.0:8000
```

Luego desde otra PC:
- http://<IP_DE_ESTA_PC>:8000/

Asegura permitir el puerto 8000 en el firewall.

## Convenciones
- Layouts: [nombre]_layout.html
- Componentes globales: templates/components/
- Componentes locales: [app]/templates/components/
- En componentes y layouts, la sección Uso debe incluir snippet de integración.
- Todo bloque de código debe llevar comentarios por secciones para legibilidad.

## Estado
En desarrollo.