# OGR Slip2D v0.1.76 — una comilla que Python 3.12 perdona y 3.11 no

## Qué se buscaba

Que el job *Test suite (Python 3.11)* de GitHub Actions vuelva a verde.
Llevaba **cinco versiones rojo** y nadie lo había mirado, porque el
resumen del fallo parecía una avalancha de tests rotos.

## Lo que era en realidad

No era ningún test. Era un `SyntaxError` **al importar**
`ogr_gui/main_window.py`, y arrastraba a todos los tests que tocan la
interfaz. La línea, introducida en v0.1.70:

```python
msg += (f"  — {tr('the total drawdown alone would overstate '
                  'it by')} {100 * margin:.1f} %")
```

Dentro del campo de sustitución de la f-string hay un literal
implícitamente concatenado y **partido en dos líneas**. PEP 701 lo
legalizó en Python 3.12; en 3.11 la f-string es un único token, así que
el salto de línea termina el literal y el fichero no se parsea.

Eso explica lo que en el panel de Actions parecía absurdo:

| Job | Resultado |
|---|---|
| Test suite (Python 3.12) | verde |
| Test suite (Python 3.11) | **rojo, `unterminated string literal`** |
| Licence consistency | verde (usa 3.12) |

Y explica también por qué el desarrollo local nunca lo vio: la máquina
tiene Python 3.14, y `pyproject.toml` declara `requires-python = ">=3.11"`
sin que nada comprobara esa promesa.

La traducción no tenía nada que ver: la clave
`"the total drawdown alone would overstate it by"` estaba correctamente
registrada en `ogr_gui/i18n/__init__.py`. Solo la sintaxis estaba mal, y
la corrección saca la llamada a `tr()` fuera de la f-string, dejando la
misma clave.

## El camino equivocado, que es la parte que merece recordarse

La herramienta obvia para «parsea esto como lo haría un Python más
viejo» es:

```python
ast.parse(src, feature_version=(3, 11))
```

**No sirve.** Se comprobó contra la revisión rota y parsea el fichero sin
una queja. `feature_version` controla un puñado de comprobaciones
semánticas y **no revierte el tokenizador** a la gramática anterior a PEP
701. Un guardián construido sobre ella habría nacido en verde y no habría
protegido nada.

El guardián que sí funciona (`tests/test_python_floor_v176.py`) trabaja
sobre tokens, y se bifurca según quién lo ejecuta:

- **corriendo en el mínimo declarado o por debajo** — `compile()` es la
  autoridad, no hay nada que aproximar;
- **corriendo por encima** (3.12+, que es el caso del desarrollo) — se
  recorre cada f-string de `FSTRING_START` a su `FSTRING_END`, contando
  anidamiento, y se rechaza que una f-string de comilla simple abarque
  más de una línea, que la comilla delimitadora reaparezca dentro de un
  `{...}`, o que haya una barra invertida dentro de un `{...}`.

Ese último matiz costó una pasada en falso: la primera versión marcaba
cualquier barra invertida y devolvía **18 hits**. Diecisiete eran `\n` en
la parte *literal* (`f"count: {n}\n"`), que Python 3.11 acepta desde
siempre. Un guardián que los rechazara se habría desactivado en una
semana. Restringida la regla al campo de sustitución, quedó **un solo
hit** — el de verdad.

El guardián lee el mínimo de `pyproject.toml` en vez de fijarlo, para que
deje de disparar solo el día que el mínimo suba a 3.12, en lugar de
sobrevivir a la restricción que protege.

### Por qué 3.11 se queda

Con el job en rojo, la salida barata era subir `requires-python` a 3.12 y
borrar el problema. Se descartó, y conviene dejar escrito por qué para no
volver a plantearlo cada vez que ese job moleste.

- **No ahorraba trabajo.** El defecto ya estaba corregido; 3.11 pasaba
  1655 de 1656 y el único fallo restante era del propio guardián.
  Subir el mínimo solo habría quitado el job que lo encontró.
- **3.11 es el Python de sistema de Debian 12**, con soporte de seguridad
  de upstream hasta octubre de 2027. Este programa se instala en máquinas
  de departamento y de laboratorio que el usuario no administra, y ahí el
  intérprete no se elige.
- **La asimetría manda**: subir el mínimo más adelante es una línea;
  bajarlo no lo es, porque para entonces la sintaxis nueva se ha colado
  sola. Que es exactamente cómo empezó esto — nadie decidió usar PEP 701
  en v0.1.70.

Y la razón que no vale, dicha en voz alta para reconocerla la próxima
vez: subir el mínimo *para que el job deje de estar rojo* es ajustar el
termómetro.

El guardián sí soporta que la decisión cambie: en cuanto
`requires-python` llegue a 3.12, la exploración se retira sola. Hizo
falta escribirlo, porque la primera versión de este fichero
**documentaba esa retirada sin implementarla**: con un mínimo de 3.12
habría marcado f-strings perfectamente legales como infracciones.

Y hubo que escribirlo **dos veces**. El primer intento comprobaba la
retirada falseando el mínimo y volviendo a ejecutar el test principal.
Pasaba en 3.14 y fallaba en 3.11 — porque el código que ejercitaba
trataba «en el mínimo o **por debajo**» como autoritativo, y por debajo
no lo es: un 3.11 rechazando código legal contra un mínimo declarado de
3.12 no dice nada del código, solo del intérprete. La decisión vive ahora
en una función pura, `_mechanism(running, floor)`, que se prueba **como
tabla** en lugar de simulando intérpretes:

| Corriendo | Mínimo | Mecanismo |
|---|---|---|
| 3.10 | 3.11 | ninguno — por debajo del mínimo, configuración no soportada |
| **3.11** | **3.11** | `compile()` — somos el mínimo, manda el intérprete |
| 3.12, 3.13, 3.14 | 3.11 | exploración de tokens, en lugar del intérprete que no tenemos |
| 3.12 | 3.12 | `compile()` — retirada no es lo mismo que apagada |
| 3.14 | 3.12 | ninguno — el mínimo ya legaliza todo lo que se busca |

### La tercera pasada en falso, y la más vergonzosa

El primer empujón dejó el job de 3.11 rojo otra vez, con 1655 de 1656:

```
✗ test_a_backslash_in_the_literal_part_is_not_flagged:
  AttributeError: module 'tokenize' has no attribute 'FSTRING_START'
```

**El guardián se caía en la única versión de Python para la que fue
escrito.** La bifurcación estaba puesta en el test principal —
`compile()` por debajo del mínimo, recorrido de tokens por encima — pero
los dos tests unitarios del escáner llamaban al ayudante directamente, y
`FSTRING_START` no existe antes de 3.12.

La bifurcación se ha bajado al propio `_fstring_defects`, que es donde
debía estar desde el principio: sin `FSTRING_START`, delega en
`compile()`. Así el ayudante es correcto en cualquier intérprete y sus
tests dejan de tener que saber en cuál corren.

Con una limitación que conviene dejar escrita, porque no se puede tapar:
**el constructo de PEP 701 no sirve para probar la rama de respaldo desde
una máquina moderna.** El `compile()` de 3.14 lo acepta — que es
exactamente la razón de que el recorrido de tokens exista — así que el
test que la cubre le da un error de sintaxis que rechaza toda versión, y
comprueba la fontanería: que `compile` levanta, y que el fallo vuelve
como cadena localizada en vez de como excepción. Que el constructo real
se detecte en 3.11 solo lo puede afirmar el job de 3.11.

## Un segundo hallazgo, del mismo tipo

Al ir a subir el número de versión apareció que **AGENTS.md enumera
cuatro sitios donde subirlo y hay siete**. Los tres que faltaban llevaban
congelados desde su propia versión:

| Paquete | Antes | Ahora |
|---|---|---|
| `ogr_core.__version__` | 0.1.59 | 0.1.76 |
| `ogr_gui.__version__` | 0.1.59 | 0.1.76 |
| `ogr_cli.__version__` | 0.1.59 | 0.1.76 |

Nada se rompía, que es justo el problema: `ogr_cli.__version__` decía
0.1.59 dentro de una distribución 0.1.75, así que un informe de error que
lo citara mandaba al lector dieciséis versiones al pasado.
`tests/test_version_consistency_v176.py` convierte la omisión en un fallo
de build, y comprueba de paso que existe el changelog de la versión
declarada.

## Cambios

- **Corregido** `ogr_gui/main_window.py` — la f-string de
  `_on_drawdown_sweep_done` ya no usa sintaxis de Python 3.12.
- **Nuevo** `tests/test_python_floor_v176.py` — siete tests: todo `.py`
  del repositorio se parsea con el Python mínimo declarado; el escáner
  reconoce el constructo exacto que causó esto (si nunca se le ha visto
  fallar, no es un guardián); la rama de respaldo anterior a 3.12
  devuelve los errores de sintaxis localizados; la comprobación se retira
  sola cuando el mínimo llega a 3.12; la tabla de decisión completa; una
  barra invertida en la parte literal no se marca; y el mínimo declarado
  tiene un job de CI que lo ejecuta. Los siete son independientes de la
  versión que los ejecute, que es lo que la primera entrega no cumplió.
- **Nuevo** `tests/test_version_consistency_v176.py` — tres tests sobre
  la deriva de metadatos de versión.
- **Modificado** `.github/workflows/tests.yml` — añadido Python 3.13 a la
  matriz. **3.11 se queda**: era el único job que fallaba, y quitarlo
  habría escondido el error en vez de arreglarlo.
- **Subidas** las siete declaraciones de versión a 0.1.76.

## Qué se probó

- El guardián **contra el árbol roto**, antes de corregir nada: falla
  señalando `ogr_gui/main_window.py:1706`, un solo constructo en los
  ~200 ficheros del repositorio.
- El guardián tras la corrección: los cuatro tests en verde.
- Suite completa con `QT_QPA_PLATFORM=offscreen python tests/_runner.py`.

## Qué falta por probar

- **La prueba real de esta versión no la da la máquina de desarrollo**:
  hay que ver el job *Test suite (Python 3.11)* verde en GitHub Actions.
  Con Python 3.14 en local, el fallo es irreproducible por construcción.
- El job de Python 3.13 se estrena aquí; si PySide6 diera problemas de
  rueda en 3.13, es la matriz lo que hay que ajustar, no el mínimo.

## Pendientes

1. **`ogr_cli` sigue sin aplicar el descenso rápido** — anotado en
   v0.1.72, v0.1.74 y v0.1.75. Es el objeto de v0.1.77, y la
   investigación previa ya dice que el enunciado se queda corto: el
   problema no es el descenso rápido, es que `ogr_cli.compute` no lee
   `p.settings` en absoluto.
2. **`Janbu Corrected` se puede marcar en Project Settings y no produce
   nada.** El diálogo lo da por implementado
   (`project_settings_dialog.py:302`), el `method_map` de
   `_ComputeWorker` no tiene esa entrada, y `method_map.get(mid)` →
   `None` → `continue`. El método desaparece de los resultados sin un
   aviso. Regla 7. Reportado, no corregido: la decisión es del autor.
3. **`Lowe-Karafiath` está gris con el tooltip «Not yet implemented»** y
   sí está implementado y registrado (`lowe_karafiath.py:49`). El tooltip
   miente.
4. **El campo de filtración por elementos finitos se pierde al guardar.**
   `fem_mesh` se serializa, `seepage_result` no, y
   `pore_pressure.py:236` devuelve `0.0` cuando falta. Abrir un proyecto
   FEM guardado y pulsar *Compute* sin volver a resolver la filtración da
   u = 0 en toda la superficie, en silencio — y esto es la **interfaz**,
   no solo el CLI.
5. **Ningún camino de entrada llega a los siete métodos LEM del
   registro.** La interfaz alcanza 5, el CLI 4, y son juegos distintos;
   mientras tanto `ogr-slip2d-cli methods` lista los siete.
