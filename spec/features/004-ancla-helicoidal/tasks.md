# Tareas — ancla helicoidal (D29)

Orden por riesgo, no por comodidad: lo que toca el camino común de todos los
soportes va primero, para que la suite lo juzgue con el tipo nuevo aún fuera.

## 1 · El cortante, conectado al motor

- [x] `_resisting_tangent_angle` y `_resisting_perpendicular` extraídos de
      `_support_force_angle`: la regla de qué perpendicular resiste, en un solo
      sitio
- [x] `compute_support_effects` pide `shear_at` cuando el tipo declara
      `SUPPORTS_SHEAR` —que así deja de ser una bandera sin lector— y suma el
      vector; la guarda pasa de `F <= 0` a `F <= 0 and V <= 0`
- [x] Documentado en las dos cabeceras que lo describían como opcional

## 2 · Los modos de rotura, escritos una sola vez

- [x] `SupportType.capacity_modes`, vacío por defecto
- [x] `GroutedTieback`, `GroutedTiebackFriction` y `SoilNail` lo implementan y
      su `force_at` pasa a ser `max(0, min(...))`
- [x] Test de identidad `force_at == min(capacity_modes)` sobre los nueve tipos

## 3 · Las estaciones

- [x] `BondProfile.stations`, campo con valor por defecto: ningún perfil
      existente cambia
- [x] `station_distances` / `station_value` en la clase base
- [x] `build_bond_profile` las evalúa en la misma pasada y con el mismo estado

## 4 · El tipo

- [x] `ogr_core/support/helical_anchor.py`: las siete funciones puras y el tipo
- [x] `bearing_factors` con `expm1`/`log1p` — sin umbral que calibrar
- [x] Registro y exportación en `ogr_core/support/__init__.py`
- [x] `__post_init__` fuerza un número de hélices entero
- [x] Las dos tablas congeladas del catálogo, actualizadas a propósito

## 5 · Interfaz

- [x] `_CHOICES["shaft_type"]`, traducido
- [x] `QSpinBox` para un parámetro cuyo valor por defecto es `int`
- [x] `PARAMETER_ENABLED_WHEN`: `helix_spacing` deshabilitado con una hélice
- [x] Color del tipo en el lienzo
- [x] `SupportForceDiagramWindow`, no modal, con desplegable y marca del corte
- [x] Acción **Data → Support Force Diagram…** en Interpret, deshabilitada sin
      soportes
- [x] Traducciones, con la terminología de v0.1.116 (*arrancamiento*,
      *descabezamiento*) y las tres roturas de cada uno

## 6 · Avisos del modelo

- [x] `helical_anchor_notes`: relación separación/diámetro fuera de 5–12, fuste
      no más estrecho que la hélice, y grupo que no cabe (diciendo qué
      separación se usó)
- [x] Enganchados en `settings_warnings`

## 7 · Validación

- [x] Los cinco intermedios publicados y las 77 celdas de la Tabla 111.1
- [x] El diagrama publicado cada 0,1 m, con los dos cambios de modo
- [x] El modo que gobierna, contra el color publicado
- [x] Las identidades analíticas y el límite de N_c década a década
- [x] La identidad de la tangente sobre los modelos constitutivos
- [x] 73,5309 kN/m a través del motor entero
- [x] Cortante nulo bit a bit; cortante > 0 en los nueve métodos
- [x] Regla 7, y **dónde** puede verse cada ajuste
- [x] Diálogo y menú, offscreen y sobre los widgets reales

## 8 · Publicación

- [x] Siete sitios de versión, 0.1.123 → 0.1.124
- [x] `docs/plugins.md`: estaciones, `capacity_modes`, `SUPPORTS_SHEAR` con
      lector, `PARAMETER_ENABLED_WHEN` y el editor entero
- [x] Changelog
- [x] Banco: modelo del 111, ficha, `referencia.json`, auditoría y comparativa
- [x] Suite entera **sin argumentos** — 2647 / 2647
