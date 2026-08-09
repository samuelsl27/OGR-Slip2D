# Casos de validación

**Esto es lo más valioso del repositorio.** Un motor de cálculo no vale por
sus funciones, sino por los casos cuyo resultado correcto se conoce y
reproduce.

## Casos

| Caso | Qué fija | Fuente |
|---|---|---|
| `001-acads-1a` | La **búsqueda**: el círculo crítico hay que encontrarlo | Giam & Donald (1989), problema ACADS 1(a) — media de 33 programas |

Los casos que fijan un **método** —evaluando un círculo ya conocido— viven
por ahora en `tests/test_slide_validation_ej1.py`.

## Qué va aquí y qué no

| Va aquí (se versiona) | Se queda fuera (no se versiona) |
|---|---|
| El modelo `.ogr` | Los archivos de proyecto del software comercial |
| El valor esperado y **su fuente** | Capturas de pantalla de otro programa |
| El test que lo comprueba | Informes PDF de terceros |

La distinción es de copyright, no de comodidad: el `.ogr` es tuyo y el
número esperado es un hecho citable; el archivo nativo y el informe de otro
programa son material de terceros.

## Estructura de un caso

```
validacion/casos/NNN-nombre-corto/
├── caso.md          ← qué es, de dónde sale el valor esperado
├── modelo.ogr       ← el modelo, listo para abrir
└── esperado.json    ← los valores de referencia, legibles por el test
```

## `esperado.json`

```json
{
  "id": "001-talud-homogeneo",
  "fuente": "Autor (año), título, página o figura",
  "tolerancia_relativa": 0.01,
  "fos": {
    "bishop_simplified": 1.372,
    "spencer": 1.379
  },
  "notas": "Cualquier condición que el caso exija: número de dovelas, tipo de presión intersticial, etc."
}
```

El bloque `busqueda` decide **con qué se ejecuta** el caso, y admite `tipo`
(cualquiera de las seis estrategias: `grid`, `slope`, `auto_refine`, `block`,
`path`, `simulated_annealing`), `num_slices`, `num_surfaces` y `semilla`. Lo
que no se declare sale del propio `modelo.ogr`, que es lo normal: así se
valida el análisis que el proyecto describe.

Hasta v0.1.78 el runner ignoraba `tipo` y ejecutaba siempre una rejilla con
sus parámetros por defecto, de modo que un caso podía estar validando algo
distinto de lo que decía.

**La tolerancia va en el caso, no en el test**, porque depende de la
calidad de la fuente: un valor leído de una figura no merece la misma
exigencia que uno tabulado.

## Añadir un caso

1. Construye el modelo en OGR Slip2D y guárdalo como `modelo.ogr`.
2. Escribe `caso.md` explicando la geometría, los materiales y **de dónde
   sale el número esperado**. Sin fuente, un valor esperado no es más que
   una opinión.
3. Rellena `esperado.json`.
4. El test `tests/test_validation_cases.py` los recorre todos
   automáticamente: no hay que escribir un test por caso.

## Si el caso falla

**No toques el caso para que pase.** Si un valor de referencia no se
reproduce, el fallo está en el código o en el propio valor — y averiguar
cuál de los dos es exactamente el trabajo que hace útil un caso de
validación.

## Comparaciones con software comercial

Sirven, y son bienvenidas, pero con dos condiciones: el número se cita como
*"obtenido con [programa], versión X"* sin adjuntar sus archivos, y **una
comparación no es una validación**. Dos programas pueden equivocarse igual;
solo un valor publicado o una solución analítica es una referencia de
verdad. Anótalo en `caso.md`.
