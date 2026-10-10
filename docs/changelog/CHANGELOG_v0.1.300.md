# OGR Slip2D v0.1.300

**`server_info` avisa cuando el servidor MCP y la ventana a la que reenvía
las llamadas tienen versiones distintas, y dice qué reiniciar (D296).**
Tercera y última versión de la tanda P8d.

## 0. Lo que se encontró

- **El síntoma** (primera prueba de la interfaz, H0). Claude Desktop había
  arrancado su servidor `ogr-slip2d` antes de que se actualizara el código.
  - `server_info` decía `"version": "0.1.271"`, y otra vez `"0.1.275"`.
  - Al mismo tiempo, el título de la ventana decía v0.1.284 y
    `next_call_goes_to` era la ventana abierta.
  - No avisó de nada. Tras reiniciar Claude Desktop, el servidor era 0.1.284.
- **Por qué importa.** Un servidor viejo enseña al agente sus herramientas,
  sus esquemas y su guía, mientras las operaciones corren en la ventana
  nueva, y el agente no tiene cómo saberlo.
- **Lo que sabía el servidor de la ventana:** solo el título y el pid.
  - Ni el saludo del puente ni el archivo de descubrimiento llevaban la
    versión.
  - La única pista era el «vX» dentro del título, que nadie comparaba.

## 1. Qué cambia

- **La ventana dice su versión:**
  - en el saludo del puente (`"version"`, junto a `"window"` y `"pid"`);
  - en su archivo de descubrimiento.
- **`BridgeClient.version`** la guarda. Es `None` si la ventana no la manda.
- **`WindowRouter.status()`** la da en `attached_to_window`.
- **`server_info` tiene un campo nuevo, `warnings`,** vacío salvo que haya
  algo que decir (`ogr_mcp.server.version_warnings`). Si la versión de la
  ventana no es la del servidor, el aviso nombra las dos y dice qué hacer:
  - **el servidor es más viejo:** se arrancó antes de actualizar. Hay que
    reiniciar el cliente MCP, que es quien lo arranca;
  - **la ventana es más vieja:** se abrió antes de actualizar. Hay que
    guardar, cerrar y volver a abrir OGR Slip2D;
  - **la ventana no dice su versión:** como el saludo la lleva desde 0.1.300,
    la ventana es anterior a esa versión, y el aviso pide lo mismo que en el
    caso anterior;
  - **sin ventana abierta:** no hay nada que comparar ni nada que decir.
- **La guía del servidor** (`ogr://guide`) lo menciona en la sección de la
  ventana.

**Lo que no se mueve:**
- el token del puente y el del HTTP;
- el modo por defecto de v0.1.207 (la ventana, si está abierta);
- el protocolo sigue siendo `ogr-slip2d-bridge/1`: la versión es un campo
  más, y una ventana vieja con un servidor nuevo sigue funcionando, ahora
  con aviso.

## 2. Tests

`tests/test_bridge_version_v1300.py`, 7 casos:
- **la ventana real** manda la versión en el saludo y la escribe en el
  archivo de descubrimiento;
- **`BridgeClient`** la guarda de un saludo que la trae, y queda en `None`
  si no la trae. Se prueba con un servidor de sockets mínimo;
- **`server_info`,** con un router hacia una ventana falsa:
  - la misma versión no da ningún aviso;
  - con el servidor más viejo, el aviso nombra las dos versiones y dice
    «Restart the MCP client»;
  - con la ventana más vieja, dice «reopen OGR Slip2D»;
  - con una ventana que no dice su versión, lo mismo, nombrando 0.1.300;
  - sin ventana, no dice nada.

Con el código de 0.1.299 fallan los 7: falta el campo `warnings`, falta
`version` en el saludo, y `BridgeClient` no tiene el atributo `version`.

## 3. Verificación

- **Suite entera:** 5955/5955, código de salida 0, tres veces sobre el mismo
  árbol. Antes hubo dos corridas cortadas; ver más abajo.
- **Tests del puente, del router, del servidor MCP y de versiones** (5
  archivos, 47 casos): verdes, salvo el del changelog, que esperaba este
  archivo.
- **Banco:** `d296()` en `verificar_cierres.py` → CUBIERTO POR TEST.

### Dos corridas cortadas, y por qué no se atribuyen al código

Las dos primeras corridas de la suite, lanzadas desde Git Bash a las 18:09 y a
las 18:52, murieron:
- a los 41,7 y 40,2 minutos, las dos en el mismo test: el 3679 de 5955, al
  entrar en `TestGlobalMinimumEngine` de `test_probabilistic_v135.py`;
- con código 127, sin totales ni traza;
- sin ningún test fallado hasta ese punto;
- sin ningún evento de error de aplicación en el registro de Windows.

Lo comprobado después, siempre sobre el mismo árbol:

| Corrida | Lanzada desde | Resultado |
|---|---|---|
| 1.ª | Git Bash | muere a los 41,7 min, test 3679 |
| 2.ª | Git Bash | muere a los 40,2 min, test 3679 |
| 3.ª | `cmd`, con `faulthandler` | 5955/5955, código 0 |
| 4.ª | Git Bash, con `faulthandler` | 5955/5955 |
| 5.ª | Git Bash, la orden exacta de la 1.ª y la 2.ª | 5955/5955 |

Además:
- el archivo `test_probabilistic_v135.py` solo pasa 18/18, y también detrás
  del test nuevo (25/25);
- ese test no reparte la búsqueda en procesos: son 175 círculos, por debajo
  del umbral de 400.

**Lectura:** la 5.ª corrida repite la orden exacta y pasa, así que el corte
no lo produce el código. Es compatible con algo externo que terminó el
proceso a los ~40 min durante esa franja de la tarde. El mismo tiempo cae en
el mismo test porque las corridas avanzan al mismo ritmo. La causa no se
conoce.

**Un dato aparte:** en esta máquina la suite tarda 50–72 min en todas las
corridas de la sesión (desde 0.1.278 al menos), no los «unos 25 minutos» que
dice AGENTS.md.

## 4. Pendiente

- **Prueba manual** con Claude Desktop: actualizar el programa sin
  reiniciar el cliente y llamar a `server_info`. El primer servidor que
  tendrá este aviso es el de 0.1.300; uno anterior no puede darlo.
