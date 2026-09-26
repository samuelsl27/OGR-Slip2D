# Censo P3 del desembalse y del cribado (D184, D194, D200), OGR 0.1.211

Generado por `_tools/censo_p3_desembalse.py` del banco de verificacion (fuera de git), sobre el 095-098: circulos publicados y busquedas enteras de todos los metodos activos, `parallel_search = False`. Un arbol por corrida; `comparado_con` es el censo del arbol anterior al arreglo.

## Resumen

- `version`: 0.1.211
- `arbol_medido`: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D
- `modulo_medido`: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D\ogr_slip2d\__init__.py
- `completo`: True
- `segundos`: 3559.9
- `problemas`: ['095', '096', '097', '098']
- `busquedas`: ['096:bishop_simplified', '096:corps_engineers_1', '096:corps_engineers_2', '096:gle_morgenstern_price', '096:janbu_simplified', '096:lowe_karafiath', '096:ordinary_fellenius', '096:spencer', '097:bishop_simplified', '097:ordinary_fellenius', '098:bishop_simplified', '098:ordinary_fellenius']
- `C_superficies`: 22488
- `D184_LLAMADAS`: {'screen_surface': 22492, 'screen_surface[m]': 22492, 'm_alpha_check': 21732}
- `D184_EXCEPCIONES_DEL_CRIBADO`: 0
- `D184_excepciones`: []
- `D184_SCREEN_ERROR`: 0
- `D184_CONTROL_VE_EL_CASO`: True
- `D194_SIN_FACTOR_POR_ETAPA`: {'1': 37, '2': 19, '3': 0}
- `D194_BUSQUEDAS_QUE_REVIENTAN`: []
- `D194_razon_no_aplica_publicada`: 280
- `D194_ETAPA1_NO_CONVERGIDA_CON_FACTOR`: 796
- `D194_etapa1_no_convergida_y_superficie_valida`: 643
- `D194_CONTROL_VE_EL_CASO`: True
- `D200_RAMA_CICLO`: 139
- `D200_rama_ciclo_por_busqueda`: {'096:bishop_simplified': 5, '096:corps_engineers_1': 15, '096:corps_engineers_2': 20, '096:janbu_simplified': 27, '096:ordinary_fellenius': 3, '097:ordinary_fellenius': 1, '098:bishop_simplified': 34, '098:ordinary_fellenius': 34}
- `D200_RECHAZADAS_POR_CRITERIO`: {'llamante': 3, 'cuernos': 26, 'ultimo_cuerno_centro': 26, 'llamante_signo_invertido_m_alpha': 29}
- `D200_VEREDICTO_LLAMANTE_DISTINTO_DE_CUERNOS`: 23
- `D200_PUBLICA_DOVELAS_DEL_LLAMANTE`: 0
- `D200_MINIMOS_QUE_CAMBIAN_ENTRE_CRITERIOS`: []
- `D200_RECONSTRUCCION_COINCIDE`: True
- `D200_CONTROL_VE_EL_CASO`: True
- `comparado_con`: 0.1.210
- `arbol_comparado`: worktree temporal de 0.1.210
- `B_FILAS_QUE_CAMBIAN`: []
- `C_MINIMOS_QUE_CAMBIAN`: []
- `sin_pareja`: []

## Circulos publicados

| problema | metodo | archivado | fos | valido | admisible |
|---|---|---|---|---|---|
| 095 | corps_engineers_1 | 1.404539 | 1.404539 | True | True |
| 096 | bishop_simplified | 1.445254 | 1.445254 | True | True |
| 097 | bishop_simplified | 0.828586 | 0.828586 | True | True |
| 098 | bishop_simplified | 0.883066 | 0.883066 | True | True |

## Busquedas enteras

| problema | metodo | minimo | superficies | ciclo | rechazadas (llamante / cuernos / ultimo cuerno) | sin factor (etapa 1/2/3) | etapa 1 no convergida |
|---|---|---|---|---|---|---|---|
| 096 | bishop_simplified | 1.451636 | 1380 | 5 | 0 / 2 / 2 | 0/0/0 | 0 |
| 096 | corps_engineers_1 | 1.4627 | 1380 | 15 | 0 / 0 / 0 | 0/0/0 | 331 |
| 096 | corps_engineers_2 | 1.462927 | 1380 | 20 | 0 / 0 / 0 | 7/0/0 | 358 |
| 096 | gle_morgenstern_price | 1.449558 | 1380 | 0 | - / - / - | 0/7/0 | 0 |
| 096 | janbu_simplified | 1.263945 | 1380 | 27 | 0 / 21 / 21 | 0/0/0 | 0 |
| 096 | lowe_karafiath | 1.449929 | 1380 | 0 | - / - / - | 0/0/0 | 90 |
| 096 | ordinary_fellenius | 0.98606 | 1380 | 3 | 0 / 0 / 0 | 0/0/0 | 0 |
| 096 | spencer | 1.446584 | 1380 | 0 | - / - / - | 0/7/0 | 17 |
| 097 | bishop_simplified | 0.818404 | 4202 | 0 | - / - / - | 16/2/0 | 0 |
| 097 | ordinary_fellenius | 0.627677 | 4202 | 1 | 0 / 0 / 0 | 7/3/0 | 0 |
| 098 | bishop_simplified | 0.892992 | 1522 | 34 | 3 / 3 / 3 | 5/0/0 | 0 |
| 098 | ordinary_fellenius | 0.77765 | 1522 | 34 | 0 / 0 / 0 | 2/0/0 | 0 |

## Controles positivos

```
{
  "d184": {
    "is_admissible": false,
    "admissible": false,
    "nota": "admissibility checks could not be evaluated (RuntimeError: CONTROL_D184)",
    "razon": "screen_error",
    "excepciones_vistas": 1,
    "admitida_sin_nota": false,
    "ve_el_caso": true
  },
  "d194": {
    "salida": {
      "valido": false,
      "razon": "m_alpha_collapsed",
      "mensaje": "Stage 3 (drained cap, pass 1) produced no factor of safety: sintetica"
    },
    "fila": {
      "metodo": "bishop_simplified",
      "revienta": null,
      "pasadas": 3,
      "etapa_sin_factor": 3,
      "razon_interior": "m_alpha_collapsed",
      "etapa1_no_convergida_con_factor": false,
      "rama": "sin_resultado",
      "fos": null,
      "valido": false,
      "admisible_interior": true,
      "razon_publicada": "m_alpha_collapsed"
    },
    "ve_el_caso": true
  },
  "d200": {
    "llamante": [
      true,
      ""
    ],
    "cuernos": [
      [
        true,
        ""
      ],
      [
        false,
        "m_alpha"
      ]
    ],
    "limite": 0.5,
    "min_m_alpha": {
      "llamante": 1.011148,
      "cuernos": [
        0.851708,
        0.226455
      ]
    },
    "ve_el_caso": true
  }
}
```

