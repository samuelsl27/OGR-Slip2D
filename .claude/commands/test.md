---
description: Ejecuta la suite completa y resume solo lo que falla
---
Ejecuta la suite de tests del proyecto:

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py
```

Después:

1. Da el recuento total (pasados / fallados).
2. Si algo falla, para **cada** fallo indica: qué invariante protegía el
   test, qué valor esperaba y cuál obtuvo.
3. **No corrijas nada todavía.** Diagnostica y espera mi OK.

Si la suite tarda más de lo que permite tu entorno, ejecútala por mitades
alfabéticas de `tests/test_*.py` y suma los recuentos, indicándolo.
