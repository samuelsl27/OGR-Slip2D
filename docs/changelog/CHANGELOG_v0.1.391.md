# OGR Slip2D v0.1.391

**Una linealización resuelve el contexto de la dovela una vez, no una por tensión** (V12 de la fase 3 de la auditoría
del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido en K13** (Tutorial 20, Bishop no circular con un material Generalized Anisotropic), con una corrida por
proceso nuevo y en orden ABBA:
- de 36,3 y 38,2 s a **31,9 y 32,4 s (−13 %)**;
- las 2876 evaluaciones, idénticas en las cuatro corridas.

Clase A: el mismo modelo leído en las mismas tensiones. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a
0.1.377.

## 0. Lo que se encontró

- **Medida otra vez después de V11**, como estaba anotado: V11 ya había dividido por nueve las linealizaciones de K13.
  - Quedan 933 523 linealizaciones y 2 779 738 lecturas con contexto, 2,98 por linealización.
  - Cada lectura volvía a buscar la regla que contiene la base, a 1,85 µs cada vez.
  - Resolverla una vez por linealización ahorraba unos 3,4 s de 34,3 (≈ −10 %). El A/B mide 5 s: −13 %.
- **Por qué tres lecturas:** `local_c_phi` lee la resistencia en la tensión de la dovela y en sus dos vecinas (la
  secante centrada), o en dos cerca de cero. Con Generalized Anisotropic, cada lectura pasaba el ángulo a grados,
  buscaba la regla y consultaba la caché del hijo.
- **Las condiciones del plan, cumplidas:**
  - **la fórmula vive en un solo sitio** (la lección de D210): el `shear_strength_ctx` de Generalized Anisotropic y su
    lector nuevo usan la misma resolución privada, `_ctx_reader`;
  - **una subclase con un `shear_strength_ctx` propio no se salta:** se lee por el suyo, como antes. Que la resolución
    sea privada evita además una recursión, la de una subclase cuyo `shear_strength_ctx` llama al del padre (lo encontró
    un mutante);
  - **el valor por defecto es un método de `StrengthModel`,** que no cambia nunca, así que no es una fuga.

## 1. Qué cambia

- `ogr_core/materials/strength_model.py`:
  - **`StrengthModel.shear_strength_reader(ctx)`:** la resistencia en un contexto como función de σ'ₙ sola. Por defecto
    llama a `shear_strength_ctx` en cada lectura;
  - **`local_c_phi`** pide el lector una vez y lo lee en las dos o tres tensiones. Si resolver el contexto lanza, lo
    hace antes de leer la primera tensión, que es donde lanzaba.
- `ogr_core/materials/builtin_models.py`, Generalized Anisotropic:
  - **`_ctx_reader(ctx)`** resuelve una vez el ángulo y la regla (o la base y las juntas de «Angle or Surface»);
  - **`shear_strength_ctx`** es ese lector leído una vez;
  - **`shear_strength_reader`** devuelve el lector, salvo para una subclase que redefine `shear_strength_ctx`.
- `tests/test_strength_reader_v1391.py`, nuevo: 7 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_strength_reader_v1391.py`:**
  - **la linealización es la de 0.1.390, bit a bit.** Su `local_c_phi` y el `shear_strength_ctx` de Generalized
    Anisotropic están copiados en el test. Se compara (c, tan φ) para los dos modos de Generalized Anisotropic (con un
    hijo Mohr-Coulomb, uno de curva potencial y uno SHANSEP), Anisotropic Linear, SHANSEP y un Mohr-Coulomb, en nueve
    ángulos de base y cinco tensiones, incluidas las de la secante de un solo lado;
  - **la sonda de resistencia nula**, con la tensión vertical sustituida;
  - **una regla por linealización**, contada;
  - **un modelo que no puede responder lanza lo mismo:** una base que no contiene ninguna regla y una regla cuyo modelo
    no se puede construir dan el mismo tipo y el mismo mensaje;
  - **una subclase con fórmula propia** se lee por ella y no entra en bucle.
- **Cinco mutantes,** cada uno cazado:
  - sin la guarda de subclase;
  - resolviendo en cada lectura;
  - el ángulo ignorado en «Angle or Surface»;
  - el contexto ignorado para un hijo que lo necesita;
  - el `shear_strength_ctx` llamando al lector público, que entra en recursión.
- **Los tests de anisotropía, resistencia, coeficientes de diseño y fugas,** juntos: 365 de 365.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0). K13, en
  su corrida de identidad: de 33,4 s (0.1.390) a 30,7 s.
- **La suite entera con `--jobs 4`:** **6859 de 6859, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 25 min.

## 3. Lo que queda

- **V13–V18,** cada una con su OK. La siguiente es V13: los flujos del solucionador de filtración, solo para el
  resultado publicado.

## Archivos

- `ogr_core/materials/strength_model.py`
- `ogr_core/materials/builtin_models.py`
- `tests/test_strength_reader_v1391.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.391.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
