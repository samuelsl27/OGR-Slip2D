---
description: Ejecuta la suite completa y resume solo lo que falla
---
Ejecuta la suite de tests del proyecto, entera y en cuatro procesos (lo
que pide publicar desde v0.1.376):

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py --jobs 4
```

Tarda unos 35 minutos: lánzala en segundo plano y guarda el código de
salida. Si `$ARGUMENTS` dice «rápida», usa `--fast --jobs 4` y avisa de
que es una corrida filtrada (`FILTERED RUN`), que no vale para publicar.

Después:

1. Da el recuento total (pasados / fallados) y, si aparecen, `Leaks: N` y
   `Chunks died: N`:
   - desde v0.1.374, un archivo que deja estado global cambiado
     (`✗ [LEAK] clave: antes → después`) hace fallar la corrida aunque
     `Failed` sea 0;
   - desde v0.1.375, un tramo que muere (`✗ [CHUNK] …`) también, con su
     código de salida y el archivo donde murió.
2. Si algo falla, para **cada** fallo indica: qué invariante protegía el
   test, qué valor esperaba y cuál obtuvo. Para una fuga, qué archivo la
   deja y qué cambia.
3. Copia las dos líneas del final si aparecen: `SERIAL RUN DUE` (toca la
   corrida en serie, sin argumentos) y `SLOW, NOT IN tests/_slow.txt`.
4. **No corrijas nada todavía.** Diagnostica y espera mi OK.
