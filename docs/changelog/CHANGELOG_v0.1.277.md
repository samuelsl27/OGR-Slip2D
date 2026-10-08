# OGR Slip2D v0.1.277

**La CI de 0.1.276 salió en rojo en las tres versiones de Python sin que
fallara ningún test.** Las tres terminaron con «Passed: 5806, Failed: 0,
Skipped: 1». Después, al cerrarse el intérprete, Qt escribió «QObject:
shared QObject was deleted directly» y el proceso murió con una violación
de segmento (código de salida 139). El motor no cambia.

## 0. Lo que se encontró

- **Lo único que 0.1.276 había añadido sobre borrados diferidos de Qt** era
  la liberación del diálogo hidráulico (D282):
  - `_define_hydraulic_properties` llamaba a `deleteLater()`;
  - su test, para comprobarlo, procesaba con
    `QCoreApplication.sendPostedEvents(None, DeferredDelete)` los borrados
    pendientes **de toda la aplicación**.
- **Por qué eso rompe el cierre.** Otros tests llaman a `deleteLater()` sobre
  ventanas que conservan en listas de módulo para que el recolector no se
  las lleve, y nadie procesa esos borrados durante la suite. Al procesarlos
  a mitad de la suite, Qt destruyó objetos que Python seguía creyendo
  suyos, y al salir Python los volvió a destruir.
- **En Windows no se reproduce:** el test solo, y por partes, sale con código
  0. En Linux el cierre de Qt es más estricto. No había un Linux local para
  confirmarlo antes de subir: lo confirma la CI de esta versión.

## 1. Qué cambia

- **`_define_hydraulic_properties`** libera el diálogo con
  `dlg.setParent(None)`. Python recupera la propiedad y lo destruye, con sus
  ventanas de gráfica, al salir de la función, sin bucle de eventos ni
  borrados diferidos.
- **El test** comprueba que la ventana no deja diálogos hijos sin procesar
  ningún borrado diferido.
- **`d282()`** del banco busca el nuevo mecanismo.

## 2. Verificación

- La suite local se lanza registrando el código de salida del PROCESO, y no
  solo el total que imprime el runner. El fallo de 0.1.276 estaba después de
  ese total.
- La CI de esta versión es la prueba de que el cierre en Linux vuelve a ir
  bien.

Suite local entera: **5807 de 5807**, con el proceso terminando con código 0.
