# OGR Slip2D v0.1.81 — el aviso llevaba dos meses en el CI, y el vigilante que iba a leerlo tampoco sabía fallar

Esta versión no cambia ni un número del cálculo. Cambia quién se entera de
que algo va mal, que es lo que resultó estar roto por partida doble.

---

## Lo que se encontró

Las cuatro tareas del CI —`test` con 3.11, 3.12 y 3.13, más `licence`—
llevaban meses imprimiendo un aviso que nadie leía:

```
Node.js 20 actions are deprecated. Please update the following actions to
use Node.js 24: actions/checkout@v4, actions/setup-python@v5
```

Y el intento de vigilar el CI para enterarse de estas cosas **se escribió
con `jq`, que no está instalado en esta máquina**. En vez de fallar, se
quedó dando vueltas en silencio. Dos guardianes distintos, el mismo
defecto: ninguno sabía fallar en voz alta. Es exactamente la queja que
este proyecto tiene con los tests de instantánea, y esta vez la teníamos
en casa.

---

## Qué es la deprecación de Node 20, exactamente

Conviene dejarlo escrito porque la confusión es fácil: **esto no tiene
nada que ver con el Python del proyecto**.

Las acciones de GitHub escritas en JavaScript no las ejecuta tu intérprete:
las ejecuta el *runner* con un Node.js propio. Cada acción declara cuál
quiere en su `action.yml`, y **el workflow no puede sobrescribirlo**:

```yaml
runs:
  using: node20        # lo que declaraban checkout@v4 y setup-python@v5
  main: dist/index.js
```

Node.js 20 llegó a su fin de vida en abril de 2026. El calendario que
publicó GitHub:

| Fecha | Qué pasa |
|---|---|
| 19-sep-2025 | Se anuncia la deprecación. Empiezan los avisos amarillos |
| **16-jun-2026** | Los runners pasan a Node 24 **por defecto**: una acción que declara `node20` sigue ejecutándose, pero **sobre Node 24** |
| **otoño de 2026** | Node 20 se elimina del runner. La escotilla `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true` deja de servir |

La fecha del medio ya había pasado cuando se miró. Es decir: no era un
aviso sobre el futuro. El CI **llevaba desde junio ejecutando dos acciones
sobre un runtime para el que no se publicaron**, y seguía en verde porque
esas dos acciones son sencillas y sobrevivieron al cambio. Esa es la clase
de cosa que funciona hasta el día que no.

Como el runtime lo fija la acción, la única salida es subir de versión.
No hay ajuste en el workflow que valga.

## Por qué v7 y no el v5/v6 que bastaba

`checkout@v5` y `setup-python@v6` fueron los primeros majors en declarar
`node24`, y con ellos el aviso también desaparece. Se ha ido a **v7 en las
dos** para no repetir el salto dentro del año. Verificado leyendo el
`action.yml` de cada etiqueta, no fiándose de las notas de la versión:

```
actions/checkout@v7      → runs.using: node24
actions/setup-python@v7  → runs.using: node24
```

### Los riesgos que se miraron antes de subir dos majors de golpe

| Lo que asustaba | Por qué no aplica |
|---|---|
| `checkout@v7` bloquea el checkout de la cabeza de un PR de fork | Solo afecta a `pull_request_target` y `workflow_run`. Este workflow dispara con `pull_request` a secas |
| `setup-python@v7` elimina la entrada `pip-install` | No se usa. Solo `python-version` y `cache: pip` |
| `cache: pip` sin `requirements.txt` en el repositorio | Sin cambio: el patrón por defecto `**/requirements.txt` no casa y cae al patrón de respaldo, igual que ya hacía con v5. En el peor caso se degrada la clave de caché; no tumba la tarea |
| Versión mínima de runner (2.327.1+) | `runs-on: ubuntu-latest`, runners de GitHub, siempre por encima |
| Node 24 no soporta macOS ≤ 13.4 ni ARM32 | No hay runners auto-alojados ni macOS en la matriz |

---

## Los dos vigilantes, uno en cada dirección

Subir la versión arregla hoy. Lo que hacía falta era que la próxima vez el
aviso llegara a alguien.

**Hacia delante: `.github/dependabot.yml`.** Vigila `github-actions`, una
vez al mes. La siguiente deprecación llega como **pull request abierto**,
que se ve esté el build verde o rojo, en lugar de como anotación amarilla,
que no.

Vigila las acciones y **nada más**, a propósito: las dependencias de
Python quedan fuera. Una subida de NumPy o Shapely tiene que pasar por los
casos de validación publicados antes de creérsela, y un PR automático
invita a fusionarla con un tick verde que demuestra menos de lo que
parece.

**Hacia atrás: `tests/test_ci_actions_v181.py`.** Dependabot avisa de lo
que sale nuevo, pero no impide volver atrás: una fusión, una reversión o
un fragmento copiado de otro repositorio pueden devolver el `@v4` a su
sitio, y el CI se pondría verde dependiendo otra vez de un runtime que ya
no existe. El test recorre los `uses:` reales de los workflows y compara
contra un suelo declarado.

No es una instantánea de lo que el YAML dice hoy —eso sería consagrar el
estado actual, que es justo lo que la regla 1 prohíbe—. Es una **política
con su motivo escrito al lado**:

```python
#: ``node24`` is the reason for both numbers, not novelty
MIN_MAJOR = {
    "actions/checkout": 7,
    "actions/setup-python": 7,
}
```

### El test que comprueba que el test puede ver

El primer riesgo de un escáner es que deje de casar y **apruebe por
silencio**: cero coincidencias, cero fallos, verde. Es la misma trampa que
la selección vacía del runner en v0.1.80. Así que antes de juzgar nada, el
archivo se obliga a demostrar que ve:

```
assert pins, "the `uses:` scan matched nothing — the guard is blind"
```

y además exige que cada acción de la tabla aparezca de verdad en algún
workflow, para que una tabla que quedó hablando de acciones retiradas
tampoco pase por vigilancia.

### Y se comprobó que grita

Un guardián se prueba haciéndolo fallar, no viéndolo pasar. Con los
workflows sustituidos por uno falso, cada regresión la caza el test que le
toca:

| Lo que se le puso delante | Resultado |
|---|---|
| `actions/checkout@v4` (vuelta atrás) | **falla** — «actions below their vetted major (these declare node20…)» |
| `actions/cache@v4` (acción nueva sin vetar) | **falla** — «actions used in CI with no vetted minimum major» |
| `actions/checkout@abc123def` (anclada a SHA) | **falla** — un SHA no lleva major, así que el suelo no se puede comprobar |
| Un workflow sin ningún `uses:` | **falla** — «the guard is blind» |

El caso del SHA es una negativa deliberada, no un agujero. Anclar por
commit es una medida de endurecimiento razonable, pero tiene que venir
acompañada de una decisión sobre cómo sigue funcionando esta comprobación,
no colarse por debajo de ella.

---

## Archivos

- `.github/workflows/tests.yml` — `checkout@v4` → `@v7` y
  `setup-python@v5` → `@v7`, en las dos tareas, con el porqué encima:
  que el runtime lo declara la acción y el workflow no lo manda.
- `.github/dependabot.yml` — **nuevo**.
- `tests/test_ci_actions_v181.py` — **nuevo**, 5 tests.
- Los siete sitios de la versión, y este changelog.
- `README.md`, `README.es.md` — el recuento de tests, otra vez al día.

## Lo que **no** se ha hecho

- **Anclar las acciones a un SHA.** Es lo que recomienda la guía de
  endurecimiento de GitHub, pero son acciones de primera parte y cada
  actualización pasaría a ser una edición a mano. Si algún día se hace,
  el test de arriba pide explícitamente que se decida antes qué comprueba.
- **Vigilar las dependencias de Python con Dependabot.** Explicado arriba,
  y el propio test lo protege: si alguien añade `package-ecosystem: pip`,
  falla y obliga a justificarlo.
- **Partir el CI en un job rápido y otro lento.** Sigue pendiente desde
  v0.1.80. Version, i18n, licencia y python floor darían aviso en menos de
  un minuto en vez de en siete.
