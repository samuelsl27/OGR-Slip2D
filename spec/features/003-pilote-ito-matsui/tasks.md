# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una tarea:
es un deseo.

## Leer la fuente antes de escribir (regla 1)

- [x] 1. Ito y Matsui (1975) leído en su escaneo: Ecs. (13), (14) y (23), y
      las Figs. 1 y 2 que definen `D₁` como distancia **entre centros** y
      `D₂` como el **hueco**. Reading Fig. 1 the other way round habría dado
      números plausibles.
- [x] 2. Cai y Ugai (2000) leído: su Ec. (10) es la (13) reescrita —**segunda
      impresión independiente**—, sus Ecs. (8) y (9) dicen cómo entra en el
      equilibrio, y su Fig. 2 y Tabla 1 publican la geometría **entera**.
- [x] 3. **La ficha del 106 era falsa**: decía que la geometría de Cai y Ugai
      «sólo aparece como captura de pantalla, sin coordenadas». La captura
      del manual **corrobora** la Fig. 2 acotada, no la sustituye.
- [x] 4. La división por `D₁` decidida **antes** de escribir, por las unidades
      y por la Ec. (9), y comprobada con un cálculo a mano sobre los datos
      publicados: `q(z) = 30,28 + 38,04·z` y ΔF ≈ 0,22 sobre 1,13.

## Las ecuaciones

- [x] 5. `ogr_core/support/ito_matsui.py`: las tres ecuaciones, puras, con su
      cita y su número, sin proyecto ni geometría.
- [x] 6. Guardas con motivo: `D₂ ≤ 0` (pilotes que se tocan) se **rechaza**,
      no se aproxima.
- [x] 7. Conmutador de φ pequeño, con el umbral **medido** y no elegido:
      1e-8 rad, donde las dos ramas coinciden a 6,4e-8 relativo.

## El modo

- [x] 8. `failure_mode`, `pile_diameter` y `force_location` en
      `PileMicropile`. **Modo y no tipo nuevo**, contra lo que pedía el
      encargo: es lo que hace la referencia, y así las dos tablas que
      congelan el catálogo no se tocan.
- [x] 9. `NEEDS_BOND_PROFILE` y `MEASURED_FROM_TOP` por **instancia**. La
      segunda importa más de lo que parece: excluiría del análisis un pilote
      dibujado horizontal, que en modo cortante es legítimo.
- [x] 10. `interface_tau` con σ'_v y con c/φ equivalentes de
      `_local_c_phi` — la linearización que ya usan los nueve métodos.
- [x] 11. `resultant_arm` con `bond`, y `BondProfile.moment` para el primer
      momento. **La firma cambió**: el muro conoce su diagrama en forma
      cerrada y un pilote no, porque su diagrama ES el perfil muestreado.
- [x] 12. Notas del modelo: agua, `q < 0`, desplome, y fila sin hueco.
- [x] 13. La nota del punto de aplicación **extraída** a
      `ogr_slip2d/support_notes.py`: dos tipos la ofrecen ya.

## La interfaz

- [x] 14. `_CHOICES["failure_mode"]` y sus traducciones. «Ito & Matsui» a la
      lista blanca como nombre propio, **sin subir el tope de 12**.
- [x] 15. **`MODE_FIELD` y `TABLE_SHOWN_FOR`, que son un defecto de D28.** El
      mecanismo estaba cableado a `profile_type`: el segundo tipo que
      declara `PARAMETER_USED_BY` recibía un combo que no deshabilitaba
      nada. Lo destapó **abrir el diálogo y mirarlo**, no razonar sobre él.

## Pruebas

- [x] 16. `tests/test_ito_matsui_pile_v1123.py`, 41 tests con su cabecera.
- [x] 17. Las dos impresiones a 8e-15; la Ec. (23) contra su re-derivación;
      el diámetro nulo a 7e-12 **absoluto**; el límite φ → 0 con la
      convergencia de primer orden comprobada década a década.
- [x] 18. **La identidad que salió de un test escrito para lo contrario**:
      la Ec. (13) es homogénea de grado uno, así que `q/D₁` depende **sólo**
      de `D₁/D`. Comprobado a 1e-16 sobre un factor 50 de tamaño.
- [x] 19. Regla 7 en las dos mitades: el punto de aplicación mueve cuatro
      métodos y **no puede** mover cinco, bit a bit.
- [x] 20. El modo cortante no se mueve un bit y no construye perfil; un
      `.ogr` de 0.1.122 abre y da el mismo número.
- [x] 21. El diálogo comprobado sobre los **dos** tipos, en los dos idiomas.
- [x] 22. Suite completa en verde, **sin argumentos**.

## El banco y el cierre

- [x] 23. Modelo del 106 construido desde Cai y Ugai Fig. 2 y Tabla 1.
- [x] 24. **Puerta (a)**, sin pilote: 1,1474 contra 1,13, **+1,54 %**, y la
      rejilla convergida (26×26 → 30×30 mueve un 0,06 %).
- [x] 25. **Puerta (b)**: la tendencia entera, las cuatro relaciones y las
      **dos** orientaciones. Clavado en 2 y 6; alto en 3 (+7,6 %) y 4
      (+3,9 %) — y **la búsqueda está agotada**, así que la explicación que
      da el propio manual no cubre este caso. Anotado, no tapado.
- [x] 26. Ficha y `referencia.json` reescritos; el 106 sale de la clase
      `huecos`; comparativa y auditoría regeneradas.
- [x] 27. D26 cerrado en `ERRORES_Y_DISCREPANCIAS.md`, con el hueco de EFW
      abierto y el residuo del 3 y el 4 anotado.
- [x] 28. Los siete sitios de versión: 0.1.122 → 0.1.123.
- [x] 29. Changelog con los caminos equivocados incluidos: el defecto de
      D28, la identidad de escala que salió de un test fallido, y la
      explicación del manual que no explica esto.
