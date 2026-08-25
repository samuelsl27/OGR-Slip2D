# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una tarea:
es un deseo.

## Medir antes de escribir (regla 6)

- [x] 1. Medir el desacuerdo entre canales — **hecho, y cambió la validación.**
      La misma fuerza horizontal en el mismo punto: Corps ×2 y Lowe-Karafiath
      a 3e-15; Ordinary, Spencer y GLE coinciden en el límite (el residuo es
      discretización: −0,009 % con 25 dovelas, +0,0006 % con 400); **Bishop
      −0,276 % y los dos Janbu −0,096 %, y no se encogen al refinar**. Abre
      **D46**. Por esto la identidad que el manual escribe no es criterio.
- [x] 2. Línea base de los seis modelos con carga distribuida (9, 25, 26, 37,
      60, 107): pesos, presiones, fuerza horizontal y su momento, dovela a
      dovela sobre una superficie fija. **Los seis idénticos bit a bit después
      del cambio.**

## El tipo

- [x] 3. `RetainingWallEFP` con las cuatro primitivas cerradas, en su propio
      módulo `ogr_core/support/retaining_wall.py`. `to_dict`/`from_dict`
      propios, listas normalizadas y copiadas.
- [x] 4. Registro y exportación en `ogr_core/support/__init__.py`.
- [x] 5. `MEASURED_FROM_TOP`: la distancia se mide desde el extremo más alto;
      un muro horizontal se excluye con su motivo.
- [x] 6. `ALLOWS_PATTERN = False`. **Corregido a mitad de camino**: se pensó
      como aviso del análisis y `SupportPattern` no deja rastro en las
      instancias que genera, así que ese aviso no habría podido dispararse
      nunca. La negativa vive donde se toma la decisión, en el diálogo.

## El motor

- [x] 7. Par `ΔM = F × (r_corte − r_centroide)`, aditivo y **exactamente cero**
      cuando los dos puntos coinciden, que es todo soporte anterior.
- [x] 8. Conectado en Ordinary, Bishop, Spencer y GLE. Medido en las **dos**
      direcciones: los cuatro se mueven un 0,09 %, los cinco restantes salen
      bit a bit iguales, y el análisis avisa nombrando los ciegos.
- [x] 9. `_surface_pressure_at` resuelve el vector; la componente horizontal
      entra por `add_water_force` con su cota.
- [x] 10. Segmento vertical: integral aplicada en el centroide, localizada por
      contención en `[xl, xr]`.

## La interfaz

- [x] 11. `_CHOICES` para `profile_type` y `force_location`; `TABLE_FIELD`
      declarado en la clase, en vez del `if TYPE_ID == "user_defined"`.
- [x] 12. Señal del combo conectada: cada forma deja habilitados sólo los
      campos que lee, y la tabla sólo aparece con el perfil personalizado.
- [x] 13. Cabeceras traducidas y en distancia relativa [0,1], con el valor
      **acotado** en vez de descartado — una fila con 1,5 es un desliz, y
      tirarla en silencio cambiaría el perfil sin decirlo.
- [x] 14. `_duplicate_row` pasa por `to_dict`/`from_dict`: la copia ya no
      comparte la lista.
- [x] 15. Color del tipo, y el tooltip deja de decir «Force at head» donde ahí
      vale cero por definición.

## Pruebas

- [x] 16. `tests/test_efp_wall_v1122.py`, 41 tests con su cabecera.
- [x] 17. Regla 7 en las dos mitades, incluida la que es fácil saltarse: el
      punto de aplicación **no puede** mover cinco métodos, y se afirma.
- [x] 18. Los seis modelos de la tarea 2, corridos otra vez: ni un dígito.
- [x] 19. Traducciones, con *Triangular* en la lista blanca y su comentario.
      **Sin subir el tope de 12** — quedaba margen para exactamente una.
- [x] 20. Alcanzabilidad comprobada, no supuesta: el tipo sale en el combo de
      *Define Support…* (8 de 8) sin tocar ningún menú.
- [x] 21. `test_seven_types_registered` → `test_the_known_types_are_registered`.
      El que sí congela el catálogo es `test_support_orientation_v1112`, que
      falló como está escrito que debe fallar y recibió la entrada del muro.
- [ ] 22. Suite completa en verde, **sin argumentos**.

## El banco y el cierre

- [x] 23. Figura 110.3 renderizada a 500 ppp. **La geometría SÍ es
      recuperable** —banqueta y = 7, coronación y = 12 (cinco pies exactos),
      muro en x ≈ −3,9, quiebro en (10 · 20,4)— y no es lo que bloquea.
- [x] 24. **El 2,566 no es alcanzable, y no por la geometría**: el enunciado no
      publica NINGUNA propiedad del suelo. *unit weight*, *cohesion*,
      *friction*, *soil* y *strength* no aparecen en su texto.
- [x] 25. Ficha y `referencia.json` reescritos (dos motivos falsos, unidades
      corregidas a imperiales); comparativa y auditoría regeneradas.
- [x] 26. D28 cerrado y **D46** abierto en `ERRORES_Y_DISCREPANCIAS.md`, con
      los cuatro defectos encontrados por el camino.
- [x] 27. Los siete sitios de versión: 0.1.121 → 0.1.122.
- [x] 28. Changelog con los caminos equivocados incluidos: la identidad falsa,
      el trapecio de una sola rampa y el aviso que no podía dispararse.
