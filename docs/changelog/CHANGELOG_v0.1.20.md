# OGR Slip2D v0.1.20 — Changelog

**Lanzamiento:** 30 de junio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> Release que añade el **método de Lowe-Karafiath** (8.º método LEM,
> equilibrio de fuerzas) validado contra referencia, y completa el
> **modo de visualización de superficies** del visor Interpret
> (Global Minimum / Minimum Surfaces / All Surfaces).

---

## 🆕 NUEVO método: Lowe-Karafiath (equilibrio de fuerzas)

Octavo método de equilibrio límite, registrado en
`ogr_slip2d/methods/lowe_karafiath.py`. Aparece automáticamente en el
selector de la GUI y en el CLI gracias al registro central de métodos.

| Método | OGR FoS | Referencia | Error |
|---|---|---|---|
| Lowe-Karafiath | 0.885974 | 0.885220 | **+0.085 %** |

**Formulación.** Es un método de **solo equilibrio de fuerzas** (no
satisface momentos). Su única hipótesis es la inclinación de la
resultante interdovela en cada interfaz:

    θ_i = ½ · ( β_i + α_i )

donde β_i es la inclinación del terreno sobre la dovela y α_i la de la
base. Eliminando la normal `N` y el cortante movilizado
`S = [c·l + (N − u·l)·tanφ]/F` de las dos ecuaciones de equilibrio de
cada dovela se obtiene una recursión lineal para la resultante
interdovela `Z`:

    Z_i = ( Z_{i-1}·D⁻ + const_i ) / D_i
    D_i = cos(α_i − θ_i) − (tanφ/F)·sin(α_i − θ_i)

El Factor de Seguridad es el que cierra la recursión con `Z_0 = Z_n = 0`
(búsqueda de raíz secante/bisección sobre F).

**Decisiones clave de implementación:**

- El force-balance de GLE/Spencer **no** es reutilizable aislado: solo
  es válido en el λ que iguala fuerzas y momentos. Lowe-Karafiath
  necesita su propia recursión de fuerzas.
- La recursión usa los **ángulos crudos con signo**. El truco de
  `slide_sign` que emplean los métodos de momentos invierte todos los
  ángulos a un signo y destruye la estructura activa/pasiva de la que
  depende la recursión de fuerzas. Se prueban ambas orientaciones de
  marcha y se usa la que produce un cambio de signo en el residual.

**🔴 Corrección de raíces espurias.** A F pequeño, `tanφ/F` crece y el
denominador `D_i` puede anularse o cambiar de signo, generando un polo
en `Z(F)` y una **raíz falsa de FoS muy bajo** (p. ej. 0.20 donde
Bishop daba 1.52 en círculos profundos). Se añade el guardado de
admisibilidad `D_i > 0` (análogo a `mα > 0` de Bishop), que poda la
región de F donde aparecen los polos. Tras el guardado, el crítico de
una búsqueda completa concuerda con Bishop dentro del ~1 % (0.9027 vs
0.8994 en el caso de prueba) en lugar de colapsar a un valor espurio.

---

## 👁️ Visor Interpret: modo de visualización de superficies

Las tres acciones del menú **Data** (que antes eran casillas sin efecto)
quedan conectadas mediante un `QActionGroup` exclusivo y un handler
`_set_surface_mode`:

- **Global Minimum** (por defecto) — dibuja solo la superficie crítica
  sobre el mapa de calor de FoS.
- **Minimum Surfaces** — las 30 superficies de menor FoS.
- **All Surfaces** — todas las superficies válidas (limitadas a 600 por
  rendimiento, dibujadas tenues y finas detrás de la crítica).

El parámetro `surface_mode` se propaga a todas las redibujadas
(selección, hover, cambio de método), de modo que el modo elegido se
conserva. El **mapa de color de FoS por método** ya funcionaba: cada
método tiene su propio resultado de búsqueda y el heatmap se recolorea
al cambiar de método en el selector.

---

## 📊 Tests

**380 tests, 369 verdes** (+6 desde v0.1.19). Los 11 fallos restantes
son los preexistentes obsoletos (`MohrCoulomb(name=...)`).

Cobertura nueva:
- `test_lowe_karafiath_reference_circle` — FoS dentro del 1 % de la
  referencia en el círculo de mínimo global riguroso.
- `test_lowe_karafiath_registered_as_force_method` — registro correcto
  (force = True, moment = False).
- `test_lowe_karafiath_grid_search_no_spurious_low_root` — regresión del
  guardado de admisibilidad: el crítico de una búsqueda completa sigue a
  Bishop dentro del 5 % y nunca colapsa por debajo de 0.5.
- `TestInterpretSurfaceMode` (5 tests) — modo por defecto, conteo de
  superficies por modo, preservación del modo al cambiar de método, y
  rechazo de modos inválidos.

---

## ⏳ Pendiente (próxima iteración)

- Corregir los 11 tests preexistentes que aún usan la firma obsoleta
  `MohrCoulomb(name=...)`.
- Resto de detalles interactivos del visor (diagrama de cuerpo libre
  ampliado, etc.) y desarrollo de funciones de análisis más allá del
  Interpret.

---

## 📦 Instalación

```powershell
Expand-Archive ogr-suite-v0.1.20.zip
cd ogr-suite-v0.1.20\ogr-suite
pip install -e .
ogr-slip2d
```

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
