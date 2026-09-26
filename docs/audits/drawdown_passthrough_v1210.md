# Censo del envoltorio de desembalse multietapa (D112b), OGR 0.1.210

Generado por `_tools/censo_desembalse_d112b.py` del banco de verificacion (fuera de git). A/B en un proceso: el brazo «antes» es el literal de 0.1.209 reconstruido sobre el mismo resultado del procedimiento, asi que el factor es identico en los dos y solo difiere lo que el chequeo y la busqueda leen.

## Resumen

- `version`: 0.1.210
- `arbol_medido`: c:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D
- `modulo_medido`: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D\ogr_slip2d\__init__.py
- `completo`: True
- `segundos`: 3534.2
- `A_archivos_multietapa`: 4
- `A_DESEMBALSE_MULTIETAPA`: {'095/modelo.ogr': 'corps_2', '096/modelo.ogr': 'duncan_wright', '097/modelo.ogr': 'corps_2', '098/modelo.ogr': 'corps_2'}
- `A_CON_JANBU_DENTRO`: ['096']
- `A_saltados`: 0
- `B_FILAS_PUBLICADAS`: 4
- `B_FILAS_PUBLICADAS_QUE_CAMBIAN`: []
- `C_BUSQUEDAS`: 7
- `C_MINIMOS_QUE_CAMBIAN`: []
- `C_superficies`: 15539
- `C_rama_ciclo`: 96
- `C_SIGNO_DISTINTO`: 0
- `C_VEREDICTOS_QUE_CAMBIAN`: 0
- `C_READMITIDAS_HASTA_0209`: {'096:janbu_simplified': 0, '096:spencer': 0, '096:gle_morgenstern_price': 0, '097:bishop_simplified': 0, '097:ordinary_fellenius': 0, '098:bishop_simplified': 0, '098:ordinary_fellenius': 0}
- `C_margen_minimo_checks`: 5.6865251705669435e-05
- `C_margen_minimo_janbu`: 5.9544705866603474e-05
- `C_CONTROL_VE_EL_CASO`: True

## Circulos publicados (filas archivadas)

| problema | metodo | archivado | antes | despues | cambia |
|---|---|---|---|---|---|
| 095 | corps_engineers_1 | 1.404539 | {'fos': 1.404539, 'valido': True, 'admisible': True, 'nota': ''} | {'fos': 1.404539, 'valido': True, 'admisible': True, 'nota': ''} | False |
| 096 | bishop_simplified | 1.445254 | {'fos': 1.445254, 'valido': True, 'admisible': True, 'nota': ''} | {'fos': 1.445254, 'valido': True, 'admisible': True, 'nota': ''} | False |
| 097 | bishop_simplified | 0.828586 | {'fos': 0.828586, 'valido': True, 'admisible': True, 'nota': ''} | {'fos': 0.828586, 'valido': True, 'admisible': True, 'nota': ''} | False |
| 098 | bishop_simplified | 0.883066 | {'fos': 0.883066, 'valido': True, 'admisible': True, 'nota': ''} | {'fos': 0.883066, 'valido': True, 'admisible': True, 'nota': ''} | False |

## Busquedas enteras

| problema | metodo | archivado | antes | despues | superficies | ciclo | signo distinto | veredictos que cambian | readmitidas hasta 0.1.209 |
|---|---|---|---|---|---|---|---|---|---|
| 096 | janbu_simplified | None | 1.263945 | 1.263945 | 1380 | 27 | 0 | 0 | 0 |
| 096 | spencer | None | 1.446584 | 1.446584 | 1373 | 0 | 0 | 0 | 0 |
| 096 | gle_morgenstern_price | None | 1.449558 | 1.449558 | 1373 | 0 | 0 | 0 | 0 |
| 097 | bishop_simplified | 0.818404 | 0.818404 | 0.818404 | 4184 | 0 | 0 | 0 | 0 |
| 097 | ordinary_fellenius | 0.627677 | 0.627677 | 0.627677 | 4192 | 1 | 0 | 0 | 0 |
| 098 | bishop_simplified | 0.892992 | 0.892992 | 0.892992 | 1517 | 34 | 0 | 0 | 0 |
| 098 | ordinary_fellenius | 0.77765 | 0.77765 | 0.77765 | 1520 | 34 | 0 | 0 | 0 |

## Control positivo

```
{
  "fila": {
    "metodo": "janbu_simplified",
    "rama": "final",
    "fos": 1.138112183886898,
    "signo_declarado": -1.0,
    "signo_respaldo": 1.0,
    "signo_janbu_publicadas": 1.0,
    "suma_checks": 34634.557642560205,
    "margen_checks": 1.0,
    "suma_janbu": 38158.428285255395,
    "margen_janbu": 1.0,
    "interior_convergido": true,
    "interior_admisible": true,
    "cuernos_admisibles": [],
    "antes": [
      true,
      true
    ],
    "despues": [
      true,
      true
    ],
    "cambia": false
  },
  "limite": 0.5,
  "m_alpha_check_antes": true,
  "m_alpha_check_despues": false,
  "ve_el_caso": true
}
```

