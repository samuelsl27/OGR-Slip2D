---
description: Comprueba que un cambio numérico está validado contra una referencia externa
---
Revisa los cambios de la rama actual (`git diff`) y, para cada cambio que
toque cálculo numérico, responde:

1. ¿Qué **referencia externa** lo valida? Un caso publicado, una solución
   cerrada o una identidad analítica. Cita autor y año.
2. Si el único respaldo es un valor que el propio código produce hoy,
   **márcalo como test de instantánea** y explica por qué no vale: un
   snapshot consagra el bug que pudiera existir.
3. ¿Se comprobó algún caso límite? (tolerancia cero, geometría
   degenerada, división por cero, rango vacío)
4. ¿Las tolerancias son **relativas** al tamaño del modelo, o absolutas?
   Las absolutas se comportan distinto en milímetros y en metros.

Devuelve una tabla: cambio · referencia · veredicto (validado / snapshot /
sin validar).
