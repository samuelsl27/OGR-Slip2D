# OGR Slip2D v0.1.523

**D460 cerrada documental.** El optimizador de los ángulos de Sarma no prueba caras paralelas a los planos
débiles, y ahora lo dice y explica por qué. Lo decidió la propietaria el 2026-11-28 (opción A). Ningún
número cambia.

## 0. Lo que se encontró

- **Qué dice la referencia.** Su página de los ángulos optimizados cuenta una optimización
  «multirresolución» y que, si hay planos débiles en el material, se prueban además caras paralelas a
  ellos. Añade que con materiales anisótropos («embedded weak planes») puede hacer falta optimizar todas
  las superficies. **No dice cómo, ni qué resistencia toma esa cara.**
- **Su página de la resistencia de las caras:** con la resistencia de los materiales, la cara toma la
  media de cᵢ y φᵢ de cada capa, ponderada por la longitud hᵢ que cruza, y con un material de
  resistencia infinita recomienda la resistencia dada. **Nada sobre los anisótropos.** No hay en
  `referencias/` ninguna fuente con una regla de resistencia de cara para un material anisótropo. Sarma
  (1979) no está: el PDF que lleva ese nombre es el de 1973.
- **Por qué un candidato paralelo no movería nada aquí:**
  - con la resistencia de los materiales, una cara que cruza un material que no es Mohr-Coulomb (los
    anisótropos incluidos) se rechaza (`lem.sarma_face_strength`);
  - con la resistencia dada o por vértice, la orientación de la cara no cambia su resistencia, y la
    búsqueda por patrones llega al ángulo que importe con el paso de 0,3125°.

  El candidato solo tendría sentido junto a una regla que diera a la cara la resistencia del plano, y esa
  regla no tiene fuente ni caso publicado con el que validarla (regla 1). Con una sin la otra sería un
  ajuste que no hace nada (regla 7).
- **La sonda de la ficha ya no da sus cifras de 0.1.485**, aunque el veredicto es el mismo:
  - con la resistencia dada sale F 0,8655813 con 672 caras probadas, frente a 0,8655808 con 679;
  - la ficha decía que el código de Sarma no había cambiado desde 0.1.471, y **sí había cambiado**:
    0.1.487 (D457), 0.1.488 (D454) y 0.1.515/0.1.517 (D450).
  - Un A/B en disco (worktrees de 5541164 = 0.1.485, c7b2c9d = 0.1.487 y b81352e = 0.1.488, con
    `PYTHONPATH`) sitúa el cambio en **0.1.487**. Con el enumerador exacto de raíces y sin la guarda del
    optimizador, la búsqueda sigue otro camino: +5,7·10⁻⁷ relativo y 7 caras menos.
  - Con la resistencia de los materiales, el rechazo sigue igual. Ninguna cara paralela, en ningún caso.

## 1. Qué cambia

- **Docstring de `ogr_slip2d/sarma/optimize_angles.py`:** párrafo nuevo, «WEAK PLANES». Cuenta qué dice la
  referencia, por qué no se prueba el candidato, que falta la regla con fuente, y la medida de esta
  versión.
- **Tooltip de los ángulos de las caras** (Ajustes → Métodos), una frase más con su español: no se prueba
  ninguna cara paralela a los planos de un material anisótropo, porque con la resistencia de los
  materiales una cara que cruza uno se rechaza, y con una resistencia dada la orientación no cambia la
  resistencia.

## 2. Tests

No hay test nuevo: es un cierre documental y ningún número cambia. Tests dirigidos
(`sarma i18n texts_details settings budget dialogs_fit`, 27 archivos): 463 en verde. El veredicto en vivo
lo da `d460()` del `verificar_cierres.py` de la raíz del banco.
