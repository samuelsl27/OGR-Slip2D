---
name: tests-numericos
description: Cómo se validan los cálculos en este proyecto. Úsalo al escribir cualquier test que compruebe un número.
---

# Validación numérica en OGR Suite

## La pregunta que hay que responder siempre

**¿Contra qué referencia externa se compara este número?**

Si la respuesta es "contra lo que el código devuelve ahora", el test es
una instantánea y **consagra cualquier bug existente**. No sirve.

## Las cuatro formas válidas

1. **Caso de referencia publicado.** Un factor de seguridad conocido.
2. **Solución cerrada.** Darcy confinado, respuesta escalón erfc, medias
   armónica y aritmética por capas.
3. **Identidad analítica.** La fuerza activa y la pasiva coinciden
   exactamente con factor objetivo 1.0. El área de las regiones iguala la
   del contorno externo. Un círculo de GSI=100 y D=0 da mb=mi, s=1, a=0.5.
4. **Consistencia asintótica.** El transitorio a tiempo grande reproduce
   el permanente.

## Tolerancias

Usa **relativas** salvo que sepas la escala. `abs(a-b) < 1e-6` sobre un
área de 5000 falla por ruido de coma flotante; `abs(a-b)/b < 1e-6` no.

## Formular el invariante honestamente

Un viaje de ida y vuelta por DXF **no** devuelve vértices idénticos, y no
debe: el saneador parte los contornos en sus cruces. La formulación
correcta es sobre la **forma**: área idéntica, todos los vértices
originales presentes, y los añadidos **sobre segmentos originales**. Es
más fuerte que exigir listas iguales, y no da por incorrecto algo que
funciona.

## Coste

Los tests que mallan y resuelven filtración son los caros. Comparte la
geometría de partida entre casos de una misma clase: un archivo pasó de
48 s a 12 s sin perder ningún test.

## Cabecera obligatoria

Cada archivo de tests empieza explicando **qué invariante protege y por
qué**, y —cuando aplique— qué bug real motivó cada comprobación.
