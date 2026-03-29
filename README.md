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
- Python 3.x
- Pipenv

## Configuración local (Pipenv)

### 1. Clonar y entrar
- git clone <URL_DEL_REPO>
- cd <CARPETA_DEL_REPO>

### 2. Crear entorno e instalar dependencias
- pip install --user pipenv
- pipenv --python 3.13
- pipenv install
- pipenv shell

### 3. Migraciones + usuario admin (opcional)
- python manage.py migrate
- python manage.py createsuperuser

### 4. Levantar servidor
- python manage.py runserver

Abrir:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/admin/

## Ejecutar en red local (LAN)
Para que otras PCs accedan desde la misma red:
- python manage.py runserver 0.0.0.0:8000

Luego desde otra PC:
- http://<IP_DE_ESTA_PC>:8000/

Asegura permitir el puerto 8000 en el firewall.

## Despliegue “producción” en Windows (LAN)
- Ver instrucciones en Notion: Instrucciones — Despliegue a producción (PR_0003)

## Convenciones
- Layouts: [nombre]_layout.html
- Componentes globales: templates/components/
- Componentes locales: [app]/templates/components/
- En componentes y layouts, la sección Uso debe incluir snippet de integración.
- Todo bloque de código debe llevar comentarios por secciones para legibilidad.

## Estado
En desarrollo.