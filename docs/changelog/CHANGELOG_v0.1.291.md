# OGR Slip2D v0.1.291

**_Preferences_ solo avisa de un cambio de idioma cuando el idioma cambia
(D290b).** Cambiar solo el tema enseñaba «Idioma cambiado. Reinicia OGR
Slip2D…», que era falso.

## 0. Lo que se encontró

- **La segunda prueba de la interfaz**, hecha por Claude Desktop sobre 0.1.290
  (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.290.md`), confirmó en
  pantalla lo corregido en 0.1.285–0.1.290:
  - la rueda, el rechazo al quitar un material en uso y el «&»;
  - los menús en gris con su motivo, en los dos temas;
  - el idioma y el tema guardados tras reiniciar;
  - todos los menús en castellano;
  - las ayudas emergentes de las cajas en gris, que la primera prueba no vio
    porque la ventana no estaba activa.
- **Lo que encontró de nuevo**, abierto en P8:
  - **D290b:** esta ficha;
  - **D302:** los botones propios de Qt salen en inglés;
  - **D291b:** textos de la ventana que D291 no alcanzó;
  - **D289b:** *Drawdown Level Sweep* no dice su motivo;
  - **D303:** el mensaje del agua nombra materiales sin uso;
  - **D304:** el panel de resultados no marca los resultados desfasados;
  - **D301:** el tema oscuro se lee mal.
- **Confirmó dos fichas abiertas:**
  - **D283,** salir sin preguntar, también por *File → Exit* y Ctrl+Q;
  - **D293,** diálogos cortados, también a 1920 × 1080 con escala 1.
- **Corrección a 0.1.290.** Su changelog dice que todos los mensajes de la
  ventana principal tienen su castellano, y no es así. Quedan los que se arman
  antes en una variable («FE mesh: …», «Transient: N stage(s) solved…») y algún
  texto que viene del núcleo. Son D291b.
- **La causa de D290b.** `PreferencesDialog._accept` emitía `language_changed`
  en cada «Guardar». Ya pasaba antes de 0.1.289, pero entonces el aviso no
  afirmaba un cambio.

## 1. Qué cambia

- **`PreferencesDialog._accept`** emite `language_changed` solo si el idioma
  elegido es distinto del activo. El tema se aplica y se guarda como siempre.

## 2. Tests

`tests/test_language_notice_v1291.py`, 3 casos sobre el diálogo real:
- con un cambio de tema y el mismo idioma, no hay señal de idioma;
- con otro idioma, sí la hay;
- con el castellano activo y «Guardar» sin tocarlo, no la hay.

Con el código de 0.1.290 fallan los dos casos que no deben avisar.

## 3. Verificación

- **Suite entera:** 5909 / 5909, con código de salida del proceso 0.
- **`verificar_cierres.py` de la raíz:** `d290b()` da CUBIERTO POR TEST;
  35 comprobaciones, ninguna bajada.
