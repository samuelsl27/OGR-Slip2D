# OGR Slip2D v0.1.161

**El encargo de P-D94 pedía estrechar un `except` que hacía desaparecer
todos los soportes a la vez, y está hecho; pero de las cuatro cosas que la
ficha da por sentadas para medirlo, la medición desmiente las cuatro: sus
dígitos son de un árbol anterior, su inventario de modelos deja fuera
precisamente el caso Activo/Pasivo de la referencia, su línea base caducó
hace una versión, y el test que pone en «no se puede mover» es el que fija
el defecto que manda corregir.**

Cierra **D94**. **Cero dígitos movidos** en el banco: los 21 problemas con
soporte corridos a 0.1.161 dan los mismos factores que 0.1.160, y el
círculo publicado del 91 —quince láminas, el refuerzo más denso del banco—
sigue en 0,9835740303049271 con Bishop y 0,9641449174231770 con Spencer.

---

## 1. El defecto

`ogr_slip2d/support_integration.py`, en `resolve_support_terms`:

```python
    try:
        effects = compute_support_effects(project, surface, slices)
    except Exception:  # noqa: BLE001
        return _EMPTY_TERMS
```

`_EMPTY_TERMS` no es «no se pudo». Es **«este modelo no lleva refuerzo»**:
`present=False` y nueve listas vacías. Los nueve métodos guardan sobre
`present` antes de indexar, así que ninguno puede distinguir las dos cosas,
y lo que sale es el factor de seguridad del talud **desnudo** con
`is_valid=True`, `admissible=True`, `error_message=''` y
`admissibility_note=''`.

Reproducido con 0.1.160 el 2026-09-12, sobre el círculo publicado del
problema 91 (centro 4,658; 15,000; R 10,934; 15 láminas; 30 dovelas),
parcheando `compute_support_effects` para que lance:

| método | con soportes | con la excepción | el mismo modelo sin soportes |
|---|---|---|---|
| bishop_simplified | 0,9835740303049271 | **0,9492210779615589** | 0,9492210779615589 |
| spencer | 0,9641449174231770 | **0,9295734702977081** | 0,9295734702977081 |

La segunda columna y la tercera coinciden **bit a bit**. No es que el
número se parezca al del talud sin refuerzo: es el mismo número.

Lo único que lo nombraba era `uncontributing_support_notes`, cuyo propio
`except` de 0.1.155 escribía la frase «this factor of safety is the one for
the slope without any of them» — pero **volviendo a llamar a la función
dentro de un `try` suyo**, y solo sobre la superficie crítica de una
búsqueda (`analysis_runner.py`). Una superficie evaluada a mano, el CLI de
superficies dadas y el `ejecutar_caso.py` del banco no pasan por ahí, así
que para ellos el silencio era total.

### La asimetría que lo explica

En el mismo bucle, `shear_at` tenía su `try` desde 0.1.124 —«a plugin must
not kill a run»— y `force_at` no tenía ninguno. El mismo plugin reventando
en la capacidad axial costaba **las quince láminas**; reventando en el
cortante costaba **un vector**. La cura es darle al axial el mismo trato
acotado que ya tenía el cortante.

---

## 2. Las cuatro cosas de la ficha que la medición desmiente

Van aquí y no en una nota al pie porque tres de ellas afectan al **criterio
de cierre**, no a la redacción.

### 2.1 Los dígitos de la ficha son de 0.1.159 y están caducados

La ficha publica 0,984824 y 0,967581. Hoy son **0,9835740 y 0,9641449**.
No se ha movido nada entre medias: 0.1.160 metió la tolerancia en cada
`.ogr` y movió 83 problemas del banco. Una ficha escrita contra un árbol y
verificada contra otro mide la subida de versión.

### 2.2 No son 19 modelos con soporte, son 21 problemas y 36 archivos

La ficha lista 030, 031, 047, 048, 049, 050, 054, 059, 060, 086–094 y 111.
Recorriendo los 111 directorios y contando `supports` en cada `.ogr`
aparecen dos más:

- **085**, con cuatro modelos (`modelo_activo`, `modelo_activo_path`,
  `modelo_pasivo`, `modelo_pasivo_path`) — que es **el** caso Activo/Pasivo
  de la referencia, el que el propio docstring de este módulo cita para
  explicar por qué el soporte llega partido en normal y tangencial;
- **106**, con cuatro (`modelo_D1D2`, `D1D3`, `D1D4`, `D1D6`).

Un criterio de cierre que no mira los dos modelos donde el Activo y el
Pasivo se separan no está midiendo este cambio. `d94()` recorre los 21.

### 2.3 La línea base tenía que ser 0.1.160, no 0.1.159

Por lo mismo del punto 2.1: `Evaluaciones/0.1.160` existe y es la
instantánea homogénea del árbol actual. Es el mismo re-anclaje que ya hizo
D79.

### 2.4 El test que la ficha protege es el que fija el defecto

`tests/test_support_silence_v1155.py::TestTheSwallowedException` está en la
lista de «QUÉ NO SE PUEDE MOVER». Su plugin `_Exploding.force_at` lanza
**`RuntimeError`** y dos de sus tres tests afirman que se traga:

```python
    terms = resolve_support_terms(p, _circle(), sl, 1.0)
    assert terms.present is False
...
    assert _result(p).fos == _result(bare).fos
```

El paso 4(b) de la misma ficha pide que un `RuntimeError` **lance**. Las
dos cosas no pueden ser verdad. Y el docstring de esa clase lo dice él
mismo: «Diagnosed here, **not fixed**: narrowing that `except` is a
separate defect and D62 may not move a number». Documentaba el defecto, no
un invariante — y ese defecto separado es este.

La clase se ha **reescrito**, con el propietario avisado antes de tocarla:
su plugin lanza ahora `SupportEvaluationError`, se le añade el caso del
`RuntimeError` que propaga, y el docstring dice dónde se corrigió. Las
otras seis clases del archivo —las de D62— no se han tocado, y sus
aserciones dan lo mismo dígito a dígito.

---

## 3. Lo que se ha hecho

### 3.1 Una excepción que significa algo

`ogr_core/support/support.py`:

```python
class SupportEvaluationError(RuntimeError):
    def __init__(self, support_id: str, reason: str): ...
```

`RuntimeError` por la misma razón que `RapidDrawdownError`: es un error de
**modelo** que el usuario tiene que resolver, no un tropiezo numérico. Y
porque el único manejador del camino de resolución atrapa `ArithmeticError`
y **no** `Exception` (`search.py`, `BaseSearch._analyse`), de modo que un
`RuntimeError` sube en voz alta salvo donde alguien lo pida a propósito.

### 3.2 Se captura donde se puede acotar el daño

**Dentro** del bucle por soporte de `compute_support_effects`, no fuera:

```python
        except SupportEvaluationError as exc:
            if reasons is not None:
                reasons.append((support.id, SUPPORT_NOT_PRICEABLE))
            if failures is not None:
                failures.append((support.id, exc.reason))
            continue
```

Así se pierde **ese** soporte y los demás siguen contando, que es la
diferencia entera con lo de antes. `SUPPORT_NOT_PRICEABLE` es la sexta
razón de la maquinaria de D62 y va la **primera** de la tupla de frases:
las otras cinco dicen qué **es** el modelo, y esta dice que el modelo no se
pudo **leer**.

Fuera del bucle —la poligonal de deslizamiento, los perfiles de adherencia,
el registro de tipos— no hay un soporte al que culpar y se pierden todos;
ahí `resolve_support_terms` captura **solo** `SupportEvaluationError` y
devuelve unos términos que llevan la razón escrita. Cualquier otra
excepción se propaga, que es la política escrita del proyecto
(`rapid_drawdown`: «has to fail loudly rather than quietly analyse
something else»).

Los otros dos `except` de este archivo —`_bond_profiles` (P-D95) y
`shear_at` (P-D98)— **no se han tocado ni aprovechado**.

### 3.3 El resultado lo dice, y la nota lo lee de ahí

`SupportTerms` gana `failure: str = ""`, el último campo, para que el
singleton posicional `_EMPTY_TERMS` siga valiendo; es `frozen=True` y
compartido, así que el caso «se perdieron todos» construye una instancia
aparte (`_failed_terms`) en vez de escribir encima —escribir encima habría
puesto el fallo de una superficie en todas las demás de la corrida—.

Los seis módulos de método pasan sus `details` por
`support_failure_details(sup, ...)`, que añade `details["support_failure"]`
solo cuando hay fallo. Y `uncontributing_support_notes` **lee ese campo**
antes de nada, en vez de volver a calcular: por eso la frase llega ahora
también a una superficie evaluada a mano, al CLI y al banco.

La clave está **ausente** —no vacía— cuando todos los soportes se pudieron
tasar, para que «no hay refuerzo» y «se perdió el refuerzo» sean dos
respuestas distintas y no una.

### 3.4 El banco

`_tools/ejecutar_caso.py` copia `details["support_failure"]` a
`avisos_circulo_publicado`, por el mismo canal que la marca INADMISIBLE de
P-D79 justo encima.

---

## 4. El censo del paso 1: qué revienta hoy

La ficha mandaba inventariar qué puede reventar dentro de
`compute_support_effects` y correr los modelos con soporte con el `except`
quitado, «si alguno revienta hoy, ese modelo lleva versiones publicando el
factor sin refuerzo sin que nadie lo supiera».

Se ha medido **envolviendo** en vez de quitando: el `except` ancho seguía
puesto durante la medición y el espía apuntaba la excepción y la volvía a
lanzar, de modo que quien estuviera arriba la siguiera tragando exactamente
igual y ni un dígito se moviera mientras se medía. El espía vive en un
`sitecustomize` y apunta a un archivo, y las dos cosas son necesarias: la
búsqueda de rejilla reparte los círculos con `ProcessPoolExecutor`, en
Windows el arranque es `spawn`, y el trabajo de verdad ocurre en procesos
hijos que no ejecutan el cuerpo de `__main__` ni comparten su memoria. La
primera versión del censo no lo tenía en cuenta y salía cuadruplicada.

**Resultado: CERO excepciones**, en los 21 problemas, 39 archivos de
resultados y los nueve métodos, búsqueda completa incluida. Ninguno de los
modelos del banco estaba publicando el factor sin refuerzo. El defecto era
real y estaba a un plugin de distancia, pero no había fuego.

Lo que sí queda dicho, porque es la mitad del valor del censo: el `except`
de `_bond_profiles` (P-D95) tampoco se disparó, y el del sentido de rotura
—el que no tiene ficha— tampoco.

### La anomalía que apareció al correr, y que no es de D94

Re-correr el 085 y el 086 —los dos que la ficha se dejaba fuera— destapó
que **`d79()` deja de sostenerse**, por dos razones y ninguna es este
cambio (la comparativa da **559 filas, las 559 IGUAL**):

1. El censo archivado de D79, `_auditoria/TRACCION_BANCO_0.1.160.md`, dice
   para el 085, literalmente:

   ```
   | 085 | gle_morgenstern_price | falta modelo.ogr |
   ```

   El 085 **no tiene** `modelo.ogr`: tiene `modelo_activo.ogr`,
   `modelo_pasivo.ogr` y sus dos gemelos no circulares. O sea que el censo
   con el que D79 estableció «y en ninguna otra» **nunca midió el 085**, y
   lo dio por limpio por ausencia de dato — que es exactamente la trampa
   que la propia ficha D79 denuncia, dentro de la herramienta de D79.

   Corrido de verdad, el 085 con GLE/M-P marca su superficie publicada
   inadmisible. Matiz que importa: ahí OGR **no publica factor ninguno**
   —`fos_en_circulo_publicado` es `None`, «GLE: no λ-bracket»—, así que no
   es un caso de «publicar el factor de una superficie inadmisible en
   silencio», que es lo que D79 persigue. Si la marca ⚠ pinta en una fila
   sin número es una decisión del código de D79 y no se toca aquí.

2. Falta `_auditoria/TRACCION_BANCO_0.1.161.md`. Es consecuencia mecánica
   de subir la versión, no de este cambio: ese censo tiene que ser de la
   versión instalada o no dice nada de este árbol.

**No se ha tocado nada de D79** —ni `D79_ESPERADO`, ni su comprobación, ni
su censo—. Queda reportado para que lo numere quien lleva la serie.

---

## 5. Lo que se probó

- `tests/test_support_failure_v1161.py`, nuevo, 16 tests en cinco bloques:
  que el fallo cuesta **ese** soporte y no los demás (identidad entre dos
  corridas del solver real, no un valor capturado); que el resultado lo
  dice y un modelo sin soportes no; que un `RuntimeError` propaga; que la
  sexta razón entra en el recuento de D62; y que el círculo publicado del
  91 sigue dando sus dos dígitos.

  **Con el motor de 0.1.160 fallan 13 de los 16**, y los tres que pasan son
  exactamente los tres que deben: las dos claves ausentes y los dígitos del
  91. Un test nuevo que pasara con el código viejo no estaría midiendo el
  defecto, y comprobarlo cuesta un `git stash`.

- `python tests/_runner.py support`: 245/245.
- La suite entera, sin filtro: **3413/3413**.
- Banco, los **21** problemas con soporte (39 archivos de resultados, los
  nueve metodos, busqueda completa), incluidos los tres no circulares del
  085/086 con `--forzar` y el 047 por su productor propio `correr_47.py`:

  | medida | resultado |
  |---|---|
  | archivos con `metodos` a 0.1.161 | 39 de 39 |
  | factores contra `Evaluaciones/0.1.160` | **145 iguales, 0 movidos** |
  | no circulares (085 activo/pasivo, 086) | **67 numeros iguales**; lo unico distinto es el cronometro |
  | `balance_evaluaciones.py` | **559 filas, las 559 IGUAL, 0 sin pareja** |
  | `verificar_cierres.py D94` | **SE SOSTIENE** |

  El 111 no entra en la cuenta: su `resultados.json` tiene esquema propio
  —la tabla 111.1 y el diagrama de fuerza del ancla helicoidal—, no lleva
  `metodos`, y lo escribe su `construir_modelo.py`.

### Qué queda sin probar, y se dice

- Los 90 problemas **sin** soporte no se han re-corrido: este cambio no
  puede tocarlos —no entra en `resolve_support_terms` un modelo sin
  `supports`— pero sus `resultados.json` se quedan en 0.1.160 y otras
  fichas los verán como PENDIENTE DE CORRIDA.
- **Nada del árbol lanza `SupportEvaluationError` todavía.** Es primero un
  contrato para el código de soportes y para los plugins, documentado en
  `docs/plugins.md`, y lo que demuestra que mueve el número es el bloque 1
  del test nuevo. Si mañana una guarda de `ogr_core/support` tiene que
  negarse a tasar un modelo, ya hay dónde decirlo.
- **Una anomalía nueva, reportada y no corregida** (regla 6): en
  `compute_support_effects`, el `try` que lee el sentido de rotura cae a
  `is_l2r = False` ante cualquier excepción, en silencio y **con
  consecuencia numérica** —invierte la dirección de fuerza de
  `TANGENT_TO_SLIP`, `HORIZONTAL` y `PERPENDICULAR_TO_PILE`, y la
  perpendicular del cortante—. No lleva `reasons` ni ficha. No se toca aquí
  porque no es el defecto de D94 y estrecharlo movería otra cosa.
