# Censo de la tension que juzgan los chequeos (D172), OGR 0.1.210

Generado por `_tools/censo_sigma_propia_d172.py` del banco de verificacion (fuera de git). El «antes» es el mismo resultado sin las dos claves nuevas: la rama sin claves es la de 0.1.209.

## Resumen

- `version`: 0.1.210
- `arbol_medido`: c:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D
- `modulo_medido`: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D\ogr_slip2d\__init__.py
- `completo`: True
- `segundos`: 42.5
- `A_archivos_ogr`: 194
- `A_con_soporte`: 36
- `A_con_envolvente_sigma_dependiente`: 5
- `A_INTERSECCION`: []
- `A_traccion_en_el_json`: 0
- `A_traccion_tras_cargar`: 0
- `A_saltados`: 0
- `A_CONTROL_VE_EL_CASO`: True
- `B_RESIDUO_DESPUES_MAX`: 1.7386699247133548e-16
- `B_RESIDUO_ANTES_MIN`: 0.5371749699164027
- `B_ORDINARIO_SIN_CLAVE`: True
- `B_metodos_medidos`: 7
- `C_superficies`: 711
- `C_MIN_LONGITUD_BASE`: 0.015768532871582863
- `C_BASES_BAJO_1E9`: 0
- `D_superficies`: 107
- `D_MAX_DELTA_M_ALPHA`: 1.3393730569077889e-12
- `D_MAX_DELTA_TANPHI_REL`: 1.5270007480694403e-12
- `D_margen_minimo_al_limite`: 0.028862523073057506
- `D_VEREDICTOS_M_ALPHA_QUE_CAMBIAN`: 0
- `D_max_delta_sigma_efectiva_rel`: 67.950902871758
- `D_traccion_que_cambiaria_si_se_encendiera`: 8
- `D_alcance`: superficies archivadas (publicadas y criticas), no poblaciones de busqueda
- `E_EJ2`: {'ordinary_fellenius': {'propia_vs_publicada': 0.0005336690358319629, 'hibrida_vs_publicada': 16.773229388657178}, 'bishop_simplified': {'propia_vs_publicada': 0.19120744104105825, 'hibrida_vs_publicada': 0.19120744104105825}, 'spencer': {'propia_vs_publicada': 4.857896632380349, 'hibrida_vs_publicada': 34.200512473105285}, 'lowe_karafiath': {'propia_vs_publicada': 4.2882089443904405, 'hibrida_vs_publicada': 36.63102943673952}, 'gle_morgenstern_price': {'propia_vs_publicada': 1.262858456537371, 'hibrida_vs_publicada': 36.413887740671235}}
- `E_MENOS_120_ANTES`: ['bishop_simplified', 'gle_morgenstern_price', 'lowe_karafiath', 'ordinary_fellenius', 'spencer']
- `E_MENOS_120_DESPUES`: ['bishop_simplified']

## B. El modelo sintetico (clavo a -15 grados, curva de potencia b = 0,6)

| metodo | activo | regla | residuo antes | residuo despues |
|---|---|---|---|---|
| bishop_simplified | True | -f_v (forma cerrada, activo) | 5.372e-01 | 1.739e-16 |
| corps_engineers_1 | True | -nf_v | 7.193e-01 | 0.000e+00 |
| corps_engineers_2 | True | - | Corps of Engineers #2: no F-bracket; reporting the sampled F of smallest residual | - |
| gle_morgenstern_price | True | -nf_v | 7.193e-01 | 0.000e+00 |
| janbu_corrected | True | -f_v (forma cerrada, activo) | 5.372e-01 | 1.739e-16 |
| janbu_simplified | True | -f_v (forma cerrada, activo) | 5.372e-01 | 1.739e-16 |
| lowe_karafiath | True | -nf_v | 7.193e-01 | 0.000e+00 |
| ordinary_fellenius | True | ninguna (su estimacion no lleva soporte) | 0.000e+00 | 0.000e+00 |
| spencer | True | -nf_v | 7.193e-01 | 0.000e+00 |
| bishop_simplified | False | lista publicada (pasivo, depende de F) | 6.362e-01 | 0.000e+00 |
| corps_engineers_1 | False | -nf_v | 7.193e-01 | 0.000e+00 |
| corps_engineers_2 | False | - | Corps of Engineers #2: no F-bracket; reporting the sampled F of smallest residual | - |
| gle_morgenstern_price | False | -nf_v | 7.193e-01 | 0.000e+00 |
| janbu_corrected | False | lista publicada (pasivo, depende de F) | 6.326e-01 | 0.000e+00 |
| janbu_simplified | False | lista publicada (pasivo, depende de F) | 6.326e-01 | 0.000e+00 |
| lowe_karafiath | False | -nf_v | 7.193e-01 | 0.000e+00 |
| ordinary_fellenius | False | ninguna (su estimacion no lleva soporte) | 0.000e+00 | 0.000e+00 |
| spencer | False | -nf_v | 7.193e-01 | 0.000e+00 |

## E. Ej_2 piezometrico: sigma' frente a las columnas publicadas

| metodo | propia - publicada (kPa) | hibrida - publicada (kPa) | -120 antes | -120 despues |
|---|---|---|---|---|
| ordinary_fellenius | 0.0005337 | 16.77 | True | False |
| bishop_simplified | 0.1912 | 0.1912 | True | True |
| spencer | 4.858 | 34.2 | True | False |
| lowe_karafiath | 4.288 | 36.63 | True | False |
| gle_morgenstern_price | 1.263 | 36.41 | True | False |

## D. Superficies archivadas de los modelos con soporte

| modelo | superficie | metodo | max dm_alpha | max dtan(phi) rel | margen | m-alpha antes/despues |
|---|---|---|---|---|---|---|
| 030/modelo.ogr | referencia:bishop_simplified:publicada | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.0837 | True/True |
| 031/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.6696 | True/True |
| 047/modelo.ogr | resultados.json:janbu_simplified:critica | janbu_simplified | 0.00e+00 | 0.00e+00 | 0.5193 | True/True |
| 047/modelo.ogr | resultados.json:janbu_corrected:critica | janbu_corrected | 0.00e+00 | 0.00e+00 | 0.5193 | True/True |
| 047/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.3948 | True/True |
| 048/modelo.ogr | referencia:janbu_simplified:publicada | janbu_simplified | 1.13e-12 | 1.02e-12 | 1.0874 | True/True |
| 049/modelo.ogr | referencia:janbu_simplified:publicada | janbu_simplified | 6.96e-13 | 1.48e-12 | 0.6423 | True/True |
| 049/modelo.ogr | referencia:janbu_corrected:publicada | janbu_corrected | 6.81e-13 | 1.48e-12 | 0.6368 | True/True |
| 049/modelo.ogr | referencia:recta_janbu_simplified:publicada | janbu_simplified | 7.81e-13 | 1.53e-12 | 0.7023 | True/True |
| 049/modelo.ogr | referencia:recta_janbu_corrected:publicada | janbu_corrected | 7.81e-13 | 1.53e-12 | 0.7023 | True/True |
| 050/modelo.ogr | referencia:por_0_0:publicada | janbu_corrected | 0.00e+00 | 0.00e+00 | 0.8000 | True/True |
| 050/modelo.ogr | referencia:por_0_-5:publicada | janbu_corrected | 0.00e+00 | 0.00e+00 | 0.6197 | True/True |
| 054/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.3007 | True/True |
| 054/modelo.ogr | resultados.json:spencer:critica | spencer | 0.00e+00 | 0.00e+00 | 0.3010 | True/True |
| 054/modelo.ogr | resultados.json:janbu_simplified:critica | janbu_simplified | 0.00e+00 | 0.00e+00 | 0.3147 | True/True |
| 054/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 0.00e+00 | 0.00e+00 | 0.3011 | True/True |
| 054/modelo.ogr | referencia:bishop_simplified:publicada | bishop_simplified | 2.94e-13 | 4.44e-13 | 0.3758 | True/True |
| 059/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.6665 | True/True |
| 059/modelo.ogr | resultados.json:spencer:critica | spencer | 0.00e+00 | 0.00e+00 | 0.7050 | True/True |
| 059/modelo.ogr | resultados.json:janbu_simplified:critica | janbu_simplified | 0.00e+00 | 0.00e+00 | 0.7423 | True/True |
| 059/modelo.ogr | resultados.json:lowe_karafiath:critica | lowe_karafiath | 0.00e+00 | 0.00e+00 | - | None/None |
| 059/modelo.ogr | resultados.json:ordinary_fellenius:critica | ordinary_fellenius | 0.00e+00 | 0.00e+00 | - | None/None |
| 059/modelo.ogr | referencia:circulo_publicado_figura_59_2:publicada | spencer | 6.73e-14 | 4.27e-14 | 0.9935 | True/True |
| 059/modelo.ogr | referencia:spencer:publicada | spencer | 6.73e-14 | 4.27e-14 | 0.9935 | True/True |
| 060/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.5023 | True/True |
| 060/modelo.ogr | resultados.json:spencer:critica | spencer | 0.00e+00 | 0.00e+00 | 0.5023 | True/True |
| 060/modelo.ogr | resultados.json:janbu_simplified:critica | janbu_simplified | 0.00e+00 | 0.00e+00 | 0.4525 | True/True |
| 060/modelo.ogr | resultados.json:lowe_karafiath:critica | lowe_karafiath | 0.00e+00 | 0.00e+00 | - | None/None |
| 060/modelo.ogr | resultados.json:ordinary_fellenius:critica | ordinary_fellenius | 0.00e+00 | 0.00e+00 | - | None/None |
| 060/modelo.ogr | referencia:spencer:publicada | spencer | 0.00e+00 | 0.00e+00 | 0.3466 | True/True |
| 085/modelo_activo.ogr | resultados_modelo_activo.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.0802 | True/True |
| 085/modelo_activo.ogr | resultados_modelo_activo.json:spencer:critica | spencer | 0.00e+00 | 0.00e+00 | 0.5152 | True/True |
| 085/modelo_activo.ogr | resultados_modelo_activo.json:gle_morgenstern_price:critica | gle_morgenstern_price | 0.00e+00 | 0.00e+00 | 0.5092 | True/True |
| 085/modelo_activo_path.ogr | resultados_no_circular_activo.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.5142 | True/True |
| 085/modelo_activo_path.ogr | resultados_no_circular_activo.json:gle_morgenstern_price:critica | gle_morgenstern_price | 0.00e+00 | 0.00e+00 | 0.5345 | True/True |
| 085/modelo_activo_path.ogr | resultados_no_circular_activo.json:spencer:critica | spencer | 0.00e+00 | 0.00e+00 | 0.5715 | True/True |
| 085/modelo_pasivo.ogr | resultados_modelo_pasivo.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.0321 | True/True |
| 085/modelo_pasivo.ogr | resultados_modelo_pasivo.json:spencer:critica | spencer | 0.00e+00 | 0.00e+00 | 0.3102 | True/True |
| 085/modelo_pasivo.ogr | resultados_modelo_pasivo.json:gle_morgenstern_price:critica | gle_morgenstern_price | 0.00e+00 | 0.00e+00 | 0.3916 | True/True |
| 085/modelo_pasivo.ogr | referencia:pasivo_bishop:publicada | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.0289 | True/True |
| 085/modelo_pasivo_path.ogr | resultados_no_circular_pasivo.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.4237 | True/True |
| 086/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 3.38e-13 | 8.74e-13 | 0.7168 | True/True |
| 086/modelo.ogr | resultados.json:spencer:critica | spencer | 3.46e-13 | 7.71e-13 | 0.7179 | True/True |
| 086/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 3.46e-13 | 7.71e-13 | 0.7178 | True/True |
| 086/modelo.ogr | referencia:spencer:publicada | spencer | 5.24e-13 | 9.17e-13 | 0.6791 | True/True |
| 086/modelo_path.ogr | resultados_no_circular.json:bishop_simplified:critica | bishop_simplified | 4.55e-13 | 1.10e-12 | 0.7867 | True/True |
| 086/modelo_path.ogr | resultados_no_circular.json:gle_morgenstern_price:critica | gle_morgenstern_price | 1.32e-13 | 7.00e-13 | 0.7828 | True/True |
| 086/modelo_path.ogr | resultados_no_circular.json:spencer:critica | spencer | 1.32e-13 | 7.00e-13 | 0.7840 | True/True |
| 087/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 9.02e-13 | 1.15e-12 | 0.5561 | True/True |
| 087/modelo.ogr | resultados.json:spencer:critica | spencer | 7.56e-13 | 9.54e-13 | 0.6713 | True/True |
| 087/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 7.56e-13 | 9.54e-13 | 0.6710 | True/True |
| 087/modelo.ogr | referencia:bishop_simplified:publicada | bishop_simplified | 9.89e-13 | 1.22e-12 | 0.7228 | True/True |
| 087/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 5.58e-13 | 7.64e-13 | 0.5562 | True/True |
| 087/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 7.48e-13 | 1.00e-12 | 0.6759 | True/True |
| 087/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 7.56e-13 | 9.54e-13 | 0.6710 | True/True |
| 088/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 5.43e-13 | 8.75e-13 | 0.7793 | True/True |
| 088/modelo.ogr | resultados.json:spencer:critica | spencer | 2.66e-13 | 4.78e-13 | 0.7798 | True/True |
| 088/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 2.67e-13 | 4.78e-13 | 0.7800 | True/True |
| 088/modelo.ogr | referencia:spencer:publicada | spencer | 4.13e-13 | 7.66e-13 | 0.7931 | True/True |
| 088/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 1.24e-13 | 1.11e-13 | 0.5301 | True/True |
| 088/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 4.18e-13 | 7.06e-13 | 0.7846 | True/True |
| 088/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 4.18e-13 | 7.06e-13 | 0.7848 | True/True |
| 089/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 6.48e-13 | 9.82e-13 | 0.9601 | True/True |
| 089/modelo.ogr | resultados.json:spencer:critica | spencer | 9.47e-13 | 1.38e-12 | 0.9607 | True/True |
| 089/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 9.47e-13 | 1.38e-12 | 0.9607 | True/True |
| 089/modelo.ogr | referencia:spencer:publicada | spencer | 5.41e-13 | 9.33e-13 | 0.9329 | True/True |
| 089/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 8.68e-13 | 1.26e-12 | 0.9622 | True/True |
| 089/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 6.87e-13 | 1.01e-12 | 0.9628 | True/True |
| 089/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 6.87e-13 | 1.01e-12 | 0.9628 | True/True |
| 090/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 9.88e-13 | 8.88e-13 | 0.6580 | True/True |
| 090/modelo.ogr | resultados.json:spencer:critica | spencer | 1.14e-12 | 1.38e-12 | 0.7083 | True/True |
| 090/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 1.01e-12 | 1.06e-12 | 0.6900 | True/True |
| 090/modelo.ogr | referencia:spencer:publicada | spencer | 7.72e-13 | 8.20e-13 | 0.8457 | True/True |
| 090/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 9.88e-13 | 8.88e-13 | 0.6580 | True/True |
| 090/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 1.14e-12 | 1.38e-12 | 0.7083 | True/True |
| 090/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 1.01e-12 | 1.06e-12 | 0.6900 | True/True |
| 091/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 9.02e-13 | 1.15e-12 | 0.5561 | True/True |
| 091/modelo.ogr | resultados.json:spencer:critica | spencer | 2.15e-13 | 3.34e-13 | 0.4413 | True/True |
| 091/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 2.14e-13 | 3.34e-13 | 0.4414 | True/True |
| 091/modelo.ogr | referencia:spencer:publicada | spencer | 9.21e-13 | 1.44e-12 | 0.4469 | True/True |
| 091/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 5.58e-13 | 7.64e-13 | 0.5562 | True/True |
| 091/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 2.15e-13 | 3.34e-13 | 0.4413 | True/True |
| 091/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 2.14e-13 | 3.34e-13 | 0.4414 | True/True |
| 092/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 7.29e-13 | 6.09e-13 | 0.8110 | True/True |
| 092/modelo.ogr | resultados.json:spencer:critica | spencer | 1.34e-12 | 1.51e-12 | 0.6576 | True/True |
| 092/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 4.73e-13 | 8.99e-13 | 0.9490 | True/True |
| 092/modelo.ogr | referencia:bishop_simplified:publicada | bishop_simplified | 7.33e-13 | 8.26e-13 | 0.8621 | True/True |
| 092/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 5.61e-13 | 3.89e-13 | 1.0117 | True/True |
| 092/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 4.77e-13 | 8.99e-13 | 0.9533 | True/True |
| 092/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 4.77e-13 | 8.99e-13 | 0.9531 | True/True |
| 093/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 8.65e-13 | 8.88e-13 | 0.5603 | True/True |
| 093/modelo.ogr | resultados.json:spencer:critica | spencer | 1.02e-12 | 1.13e-12 | 0.6382 | True/True |
| 093/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 1.30e-12 | 1.44e-12 | 0.6922 | True/True |
| 093/modelo.ogr | referencia:spencer:publicada | spencer | 7.26e-13 | 8.83e-13 | 0.7798 | True/True |
| 093/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 1.13e-12 | 1.31e-12 | 0.5605 | True/True |
| 093/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 1.02e-12 | 1.13e-12 | 0.6382 | True/True |
| 093/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 6.79e-13 | 1.03e-12 | 0.7030 | True/True |
| 094/modelo.ogr | resultados.json:bishop_simplified:critica | bishop_simplified | 1.25e-12 | 1.39e-12 | 0.5603 | True/True |
| 094/modelo.ogr | resultados.json:spencer:critica | spencer | 8.70e-13 | 1.10e-12 | 0.6724 | True/True |
| 094/modelo.ogr | resultados.json:gle_morgenstern_price:critica | gle_morgenstern_price | 8.70e-13 | 1.10e-12 | 0.6720 | True/True |
| 094/modelo.ogr | referencia:bishop_simplified:publicada | bishop_simplified | 5.87e-13 | 8.94e-13 | 0.7244 | True/True |
| 094/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:bishop_simplified:critica | bishop_simplified | 2.30e-13 | 2.22e-13 | 0.7167 | True/True |
| 094/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:spencer:critica | spencer | 8.78e-13 | 1.10e-12 | 0.6776 | True/True |
| 094/modelo_sin_conexion.ogr | resultados_modelo_sin_conexion.json:gle_morgenstern_price:critica | gle_morgenstern_price | 9.31e-13 | 1.29e-12 | 0.7600 | True/True |
| 106/modelo_D1D2.ogr | resultados_modelo_D1D2.json:bishop_simplified:critica | bishop_simplified | 0.00e+00 | 0.00e+00 | 0.4736 | True/True |
| 106/modelo_D1D4.ogr | resultados_modelo_D1D4.json:bishop_simplified:critica | bishop_simplified | 3.15e-14 | 1.17e-13 | 0.6065 | True/True |
| 106/modelo_D1D6.ogr | resultados_modelo_D1D6.json:bishop_simplified:critica | bishop_simplified | 2.35e-14 | 8.68e-14 | 0.5780 | True/True |

