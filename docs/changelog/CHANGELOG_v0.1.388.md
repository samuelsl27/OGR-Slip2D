# OGR Slip2D v0.1.388

**El modelo de un hijo de Generalized Anisotropic sale de su caché sin preguntar nada más** (V9 de la fase 3 de la
auditoría del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido en K13** (Tutorial 20, Auto Refine no circular con Surface Altering), con una corrida por proceso nuevo y
en orden ABBA:
- de 66,8 y 68,4 s a **57,8 y 59,9 s (−13 %)**;
- las 2876 evaluaciones, idénticas en las cuatro corridas.

Clase A: no toca la aritmética. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a 0.1.377.

## 0. Lo que se encontró

- **La puerta de medida.** En K13, `GeneralizedAnisotropic._child_model` se llama 6 745 641 veces y solo falla 3. En
  cada llamada, también cuando acertaba, hacía dos importaciones y construía la etiqueta del hijo («rule 2», «the
  base») antes de mirar la caché. La etiqueta solo la lee el mensaje de un hijo que no se puede construir.
- **Un acierto** pasa de 1,126 µs a 0,437 µs. Eso explica 4,6 s; el A/B mide 8,8 s.
- **Dos medidas que no valían:**
  - **El A/B en un mismo proceso** daba 60–62 s frente a 79–86 s, unos 20 s, más del doble de lo que mide el A/B en
    procesos nuevos. No se usa.
  - **La sospecha del recolector**, por las cadenas que la etiqueta creaba en cada llamada: no se sostiene, porque las
    dos versiones hacen exactamente las mismas recolecciones (213, 19 y 1 por generación).

  La cifra que vale es la de procesos nuevos, −13 %. Las corridas iguales difieren entre sí 2,1 y 1,6 s, frente a un
  efecto de 8,8 s.
- **Lo que se queda,** como pedía el plan: la comparación por valor contra la copia del diccionario, que es lo que
  detecta una regla editada en el sitio, y la comparación por identidad, que reconstruye una regla sustituida.

## 1. Qué cambia

- `ogr_core/materials/builtin_models.py`: `GeneralizedAnisotropic._child_model` mira la caché primero. Lo que hacía en
  un fallo pasa, tal cual, a `_build_child`: las importaciones, la etiqueta, la construcción y el mensaje.
- `tests/test_child_model_v1388.py`, nuevo: 4 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_child_model_v1388.py`:**
  - **lo que responde es lo de 0.1.387, llamada a llamada.** El método viejo está copiado en el test, y los dos
    recorren la misma secuencia: construcción, aciertos, una regla editada en el sitio, una sustituida por un
    diccionario igual, un hijo sin modelo y uno que no se puede construir. Se compara en cada paso el objeto devuelto o
    el tipo y el mensaje de la excepción;
  - **un acierto devuelve el mismo objeto** y no construye la etiqueta; un fallo la construye una vez;
  - **la regla editada en el sitio y la sustituida** se reconstruyen.

  Tardan milisegundos.
- **Cinco mutantes,** cada uno cazado:
  - la etiqueta construida en cada llamada;
  - sin la comparación por valor;
  - sin la comparación por identidad;
  - otro texto de mensaje;
  - sin guardar en la caché.
- **Los tests de la anisotropía y de las fugas,** juntos: 227 de 227.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0). K13, en su
  corrida de identidad: 56,6 s, frente a 64,4 y 67,8 s en las de 0.1.386 y 0.1.387.
- **La suite entera con `--jobs 4`:** **6834 de 6834, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 26 min.

## 3. Lo que queda

- **V10–V18,** cada una con su OK. La siguiente es V10: la geometría de momentos, una vez por superficie (Spencer y
  GLE en poligonales).
- **V12,** el contexto anisótropo una vez por linealización, se mide después de V11, como dice el plan.

## Archivos

- `ogr_core/materials/builtin_models.py`
- `tests/test_child_model_v1388.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.388.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
