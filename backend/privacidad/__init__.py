"""Minimización de datos personales antes de la llamada externa.

Dos piezas, deliberadamente separadas:

- `listado_local.py`: la correspondencia entre el nombre real de un alumno
  y su código. Vive solo en el equipo del docente -nunca en Supabase, nunca
  en un informe, nunca en el repositorio-.
- `minimizacion.py`: lo que se hace con el texto de una entrega antes de
  que salga hacia el motor de análisis, usando esa correspondencia y las
  mismas expresiones regulares que ya protegen el repositorio (R6).

Ninguna de las dos promete anonimizar. Ver el docstring de `minimizacion.py`
para el porqué.
"""
