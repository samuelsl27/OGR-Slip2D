# Servidor MCP: el programa manejado por un agente

## Qué hace

Expone **todo** OGR Slip2D a un agente de IA a través del Model Context
Protocol (MCP): crear y editar la geometría, los materiales, las cargas, los
soportes y el agua; configurar y lanzar cualquier análisis; y leer, interpretar
y dibujar los resultados, sin tocar la interfaz.

Tres piezas, en este orden porque cada una se apoya en la anterior:

1. **`ogr_core/project/rules.py`**: las invariantes del modelo que hoy sólo
   impone la interfaz, **movidas** —no copiadas— para que valgan igual desde
   la GUI, la CLI, un script o un agente.
2. **`ogr_api`**: una capa de operaciones sin Qt y sin `mcp`, con *handles*,
   validación, deshacer, trabajos en segundo plano, resúmenes y render.
3. **`ogr_mcp`**: la envoltura fina que publica esas operaciones con el SDK
   oficial `mcp` (MIT), por stdio y por HTTP.

Después, un **puente en vivo** con la ventana abierta (fase F4), con las mismas
operaciones y otro transporte.

## Por qué

El ingeniero quiere describir un talud en lenguaje natural, que el agente lo
construya, lo calcule y le enseñe el resultado, y poder revisarlo después en la
interfaz. Sin esta capa, un agente sólo puede escribir scripts contra clases
que aceptan en silencio un ajuste mal escrito, una búsqueda que no existe o un
enum pasado como cadena —y un factor de seguridad plausible calculado con
ajustes que nadie pidió es el peor resultado posible.

## Decisiones del propietario (2026-09-24)

- Mismo repositorio; extra opcional `[mcp]`; comando `ogr-slip2d-mcp`.
- Modo *headless* primero; puente en vivo con la GUI en F4.
- Una herramienta que ejecuta Python libre, **siempre activa**. Es, por
  diseño, ejecución de código: por eso el HTTP exige token incluso en
  *loopback* y valida `Origin`/`Host`.
- Clientes prioritarios: Claude (stdio), modelos locales con LM Studio u
  Ollama (perfil `compact`), Open WebUI (HTTP), BionicGPT (OpenAPI vía
  `mcpo`), OpenAI Agents SDK (stdio) y ChatGPT (HTTPS remoto, F4b).

## Lo que la especificación MCP 2026-07-28 impone

- El protocolo **no guarda estado**: todo lo que persiste entre llamadas viaja
  como *handle* emitido por el servidor (`project_id`, `job_id`, `result_id`).
- Las tareas largas no tienen soporte en el SDK de Python 2.x: los análisis
  largos siguen el patrón propio `analysis_run → job_id → job_get / job_cancel`,
  que funciona con cualquier cliente.
- Roots, Sampling y Logging están deprecados: no se usan.

## Criterios de aceptación

### Fase F1a — `ogr_api` (v0.1.194)

- [x] ACADS 1(a) (Giam y Donald, 1989) construido **desde cero sólo con
      operaciones de `ogr_api`** da un FoS de Bishop dentro de 0,991 ± 2 %
      (la media de los 33 programas y la tolerancia se importan de
      `tests/test_acads_validation_v178.py`, no se reescriben).
- [x] El caso de referencia Ej_1 construido con operaciones reproduce los seis
      métodos sobre el círculo publicado al 0,5 %, y su grid 20×20×10 da centro
      (88; 70,5), R = 47,2124436 y 4851 superficies.
- [x] Un campo de ajustes desconocido, un campo retirado o una errata en un
      valor enumerado se **rechazan** con una sugerencia; un lote con un solo
      error no cambia nada (`to_dict` idéntico al de antes).
- [x] Todo campo `str` o `list[str]` de las dataclasses de ajustes está
      clasificado (valor enumerado, texto libre, complejo o de sólo lectura);
      un campo nuevo sin clasificar rompe un test.
- [x] Toda operación que modifica el modelo se deshace y se rehace dejando el
      `to_dict` exactamente como estaba; una operación que falla no deja
      rastro.
- [x] Un análisis lanzado como trabajo informa progreso, no se entera de las
      ediciones posteriores al lanzamiento, se cancela sin dejar procesos
      huérfanos y, si el proceso muere, lo dice con la cola de su registro.
- [x] El render devuelve un PNG del tamaño pedido, y la superficie crítica sólo
      aparece cuando hay resultado.
- [x] `python_exec` captura la salida por hilo (dos ejecuciones concurrentes no
      mezclan su salida) y deja `sys.stdout` como estaba.
- [x] `ogr_api` no importa PySide6, `ogr_gui` ni `mcp`; el motor no importa
      `ogr_api` (test AST).
- [x] La GUI delega en `rules.py` las tres reglas movidas en esta fase y sus
      tests existentes siguen pasando.

### Fase F1b — `ogr_mcp` (v0.1.195)

- [ ] ACADS 1(a) atravesando el protocolo (cliente en memoria del SDK) da el
      mismo número que por `ogr_api`.
- [ ] Toda herramienta y todo parámetro tienen descripción; el perfil
      `compact` no supera un presupuesto de tamaño congelado.
- [ ] Un servidor stdio lanzado como subproceso sobrevive a `print`,
      `os.write(1, …)` y a un subproceso hijo que escribe en su salida
      estándar, dentro de `python_exec`.
- [ ] HTTP: sin token 401; con un `Origin` ajeno 403; con un host que no es
      *loopback* y sin token, el servidor no arranca.
- [ ] Cada una de las 136 acciones de `MainWindow._actions` está clasificada
      como `MAPPED`, `UI_ONLY` (con motivo) o `PENDING` (con la fase que la
      cubrirá), y `PENDING` sólo puede encoger.

### Fases F2–F4b

Tienen su propio plan corto antes de empezar. El criterio de cierre global es
que al terminar F4 **`PENDING` está vacío**: toda acción del programa tiene su
herramienta MCP o una razón escrita para no tenerla.

## Validación numérica

El servidor no añade ninguna fórmula: su riesgo es **llegar a otro número por
otro camino de ajustes**. Por eso la validación es la de la regla 1 con el
modelo construido por la vía nueva:

- ACADS 1(a), Giam y Donald (1989), media de 33 programas 0,991 ± 2 %.
- Ej_1, seis métodos sobre el círculo publicado (0,5 %) y el grid publicado.

Si alguno no se reproduce **no se ajusta nada**: significa que el camino de
ajustes de `ogr_api` diverge del camino validado, y se reporta.

## Idioma

Las descripciones de herramientas, los mensajes de error y la guía de
modelado del servidor van **en inglés**: los lee un modelo de lenguaje, no el
usuario en la interfaz, y el motor ya produce sus mensajes en inglés. No es un
incumplimiento de la regla 2, que es sobre texto de la interfaz. Lo que el
puente de F4 añada a la GUI (menú, avisos) sí pasa por `tr()` con su castellano.

## Fuera de alcance

- Un REST propio: BionicGPT y otros clientes OpenAPI usan `mcpo`.
- La extensión de tareas del protocolo mientras el SDK de Python no la
  implemente; cuando lo haga, el `JobManager` se publica también por ahí.
- Persistir los resultados en el `.ogr` (la decisión de `tech-stack.md` se
  mantiene).
- Corregir las anomalías encontradas durante la exploración (A1–A13 del
  changelog de v0.1.194, más A14 y la tolerancia de Ej_1): se reportan, no
  se arreglan aquí.
