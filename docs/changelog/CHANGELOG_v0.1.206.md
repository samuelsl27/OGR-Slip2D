# OGR Slip2D v0.1.206

**El `pytest.skip` de v0.1.205 se escapaba en GitHub, y la suite se paraba al
83 % sin totales.** Es un defecto que introduje en la versión anterior. Solo
se ve donde el banco de verificación no existe, y por eso no apareció en la
suite local (4545 de 4545).

## Qué pasó

La primera corrida de la CI de v0.1.205 terminó en rojo en las tres versiones
de Python, y no por un test fallado: la suite se cortó en
`test_support_failure_v1161::test_the_fifteen_sheets_give_what_they_gave`
con `_runner.Skipped: the verification bank is not on this machine`.

- El runner se ejecuta como script, así que su clase es `__main__.Skipped`, y
  eso es lo que capturaba.
- **`test_project_settings_wiring_v174` hace `import _runner`** para usar un
  ayudante. Eso ejecuta el runner otra vez como módulo, crea un segundo
  `Skipped` e **instala su propio `pytest` simulado**, que nunca devuelve a su
  sitio (regla 5).
- Desde ese archivo, `pytest.skip` lanzaba `_runner.Skipped`. El runner no lo
  reconocía, y al ser `BaseException` atravesó el bucle y terminó el proceso.
- Con el `pytest` simulado de antes la fuga no tenía efecto, porque no había
  clases cuya identidad importara. `skip` la hizo visible.

## Qué cambia

- **Un salto se reconoce por una marca** (`ogr_skip`) y no por su clase.
  Cualquier copia del runner entiende el salto de cualquier otra.
  `KeyboardInterrupt` sigue subiendo.
- **El `pytest` simulado se instala una sola vez.** Si ya hay uno del runner,
  volver a cargar el archivo no lo sustituye. `import _runner` deja de filtrar
  estado a los archivos que vienen después.

## Tests

`tests/test_runner_exit_v1203.py` gana dos casos, medidos A/B contra el
runner tal como quedó en v0.1.205:

- **`test_another_copys_skip_is_still_a_skip`.** Un salto lanzado por otra
  copia del runner cuenta como saltado.
  - Con el runner de v0.1.205, **falla**: la copia deja pasar el salto.
  - Sin la guarda del propio caso, ese salto habría llegado al runner que
    ejecuta el archivo y se habría contado como el salto de este caso: un
    defecto disfrazado de salto.
- **`test_loading_the_runner_again_keeps_the_installed_shim`.** Volver a
  cargar el runner no cambia el `pytest` instalado.
  - Se comprueba en el momento de cargar, no después, porque el cargador del
    test devuelve el `pytest` en su `finally`.
  - Con el runner de v0.1.205, **falla**.

Con la corrección pasan los ocho casos del archivo.

**Verificación:** la suite entera, sin filtros, pasa **4547 de 4547** en Windows con Python 3.14; la CI de GitHub, en la corrida de este commit.
