# Especificación de interfaz — módulo de agua subterránea

**Autor:** Samuel Sáez López — UPCT
**Fecha:** 26 de julio de 2026
**Estado:** especificación para la **Fase 5** (GUI modo Groundwater). El
motor de las Fases 0–3 ya expone todo lo que esta interfaz necesita.

Documento obtenido por **ingeniería inversa** de la documentación de la
referencia (archivos `.htm` del proyecto + páginas públicas de
documentación de Slide2 y RS2), para que la organización de opciones no
se invente sino que siga un patrón ya validado por uso real.

---

## 1. Conmutador de modo de análisis

Un selector **Analysis Mode: Slope Stability ↔ Groundwater** que cambia
menús y barra de herramientas. La geometría es compartida; malla,
propiedades hidráulicas y condiciones de contorno son exclusivas del modo
agua. Las opciones de agua **solo se habilitan** cuando
`Groundwater Method = Finite Element Analysis` en Project Settings — es
decir, hay una dependencia explícita entre ajuste y disponibilidad de
menú que conviene replicar para no ofrecer opciones inertes.

## 2. Menú *Groundwater* (modo agua)

Ordenado por el flujo de trabajo real, que es secuencial y con
dependencias duras:

```
Properties
  └── Define Hydraulic Properties…        (requiere: método = FEA)
  └── Assign Properties
Mesh
  └── Mesh Setup…
  └── Discretize
  └── Discretize and Mesh
  └── Generate Mesh                        [implementado v0.1.25]
  └── Custom Discretize…
  └── Mesh Refinement / Mesh Quality
  └── Reset Mesh                           [implementado v0.1.25]
  └── Set Boundary Conditions…             (requiere: malla existente)
  └── Set Linearly Varying Total Head…
Discharge Sections
  └── Add / Move / Stretch / Delete Discharge Section
Compute Groundwater
Interpret Groundwater
```

**Dependencias que la GUI debe hacer cumplir** (tomadas literalmente de
la documentación): *Set Boundary Conditions* está **deshabilitado si no
existe malla**; las propiedades hidráulicas solo si el método es FEA.

## 3. Diálogo *Define Hydraulic Properties*

Estructura de dos zonas, con la lista de materiales a la izquierda y los
parámetros a la derecha. Punto importante de diseño: **los nombres y
colores de material NO son editables aquí** — se heredan del diálogo de
propiedades resistentes. Son dos vistas de la misma lista de materiales,
no dos listas.

| Control | Notas |
|---|---|
| **Saturated Permeability Ks** | Siempre requerido. Se **deshabilita** si el modelo es *User Defined* (allí Ks es el primer punto de la curva). |
| **K2/K1** | Factor de anisotropía (dirección ortogonal a K1). |
| **K1 Angle** | Desde el eje +X horizontal. Acompañar de un **dibujo esquemático** en el diálogo, como hace la referencia. |
| **Model** | Desplegable: Constant, Simple, Brooks-Corey, Fredlund-Xing, Gardner, van Genuchten, + funciones User Defined por nombre. |
| **Parámetros** | Cambian según el modelo (ver tabla §4). |
| **Soil Type** | Solo con *Simple*: General, Sand, Silt, Clay, Loam. |
| **Custom m** | Solo con *van Genuchten*: libera `m = 1 − 1/n`. |
| **Botón Plot** | Grafica la función k(ψ) resultante. Motor listo: `HydraulicProperties.curve()`. |
| **Botón Pick** | Biblioteca de materiales representativos con **referencias bibliográficas visibles**. Disponible solo para Brooks-Corey, Fredlund-Xing, Gardner y van Genuchten. Motor listo: `HydraulicProperties.library()`. |
| **Botón New** | Crea una *User Defined Permeability Function*: nombre + tabla (succión, permeabilidad) con **gráfico editable arrastrando los puntos**. |

## 4. Parámetros por modelo (nombres exactos de la referencia)

| Modelo | Parámetros de usuario |
|---|---|
| Constant | — (k = Ks) |
| Simple | *Soil Type* |
| Brooks-Corey | *Pore Size Index* (λ), *Bubbling Pressure* (ψb) |
| Fredlund-Xing | *A*, *B*, *C* |
| Gardner | *a*, *n* |
| van Genuchten | *alpha*, *n*, *m* (+ *Custom m*) |
| User Defined | tabla (succión, permeabilidad) |

Estos nombres se confirmaron cruzando el diálogo con la lista de
variables aleatorias hidráulicas de la referencia (que enumera
literalmente "Brooks and Corey Pore Size Index", "Fredlund and Xing A/B/C
Parameter", "Gardner a/n Parameter", "Van Genuchten alpha/n/m
Parameter") — útil además porque anticipa qué parámetros deben ser
estadísticos cuando se aborde el análisis probabilístico.

## 5. Diálogo *Set Boundary Conditions*

| Control | Notas |
|---|---|
| **BC Type** | Lista + **iconos** en la cabecera: Total Head, Pressure Head, Zero Pressure, Nodal Flow Rate, Infiltration, Unknown (P=0 o Q=0). |
| **Value** | Solo habilitado para Total Head, Nodal Flow Rate e Infiltration. |
| **Seepage Face** (checkbox) | Solo para Nodal Flow Rate e Infiltration. |
| **Pick by** | Selector: *line segments* o *nodes*. **Infiltración solo por segmentos**, nunca por nodo. |
| Aplicación | Seleccionar con el ratón y **botón derecho → Assign**, o botón *Apply*. Diálogo no modal para asignar varias tandas seguidas. |

**Valores por defecto al mallar** (ya implementados en
`default_boundary_conditions()`): *Unknown* en la superficie del terreno
y **flujo nodal nulo** en los bordes izquierdo, derecho e inferior. La
documentación advierte que «en general habrá que personalizarlos», así
que la GUI debe mostrarlos claramente pintados sobre la malla, no
silenciosamente.

## 6. Interpret de agua

Datos a graficar (todos ya disponibles en `SeepageResult`):

- Contornos de **cabeza total H**, **cabeza de presión P** y **presión
  intersticial u** (incluida succión negativa)
- **Vectores y líneas de flujo** (velocidad de Darcy por elemento)
- **Superficie freática** = isolínea P = 0 → `free_surface_points()`
- **Secciones de descarga** con caudal integrado →
  `flux_through_segment()`
- Gradientes y velocidades

## 7. Avisos de convergencia

La documentación de la referencia advierte explícitamente que las
muestras que no convergen se excluyen de los resultados. Nuestro solver
ya devuelve `notes["warning"]` con el cambio residual y una sugerencia
(reducir el factor de relajación o refinar la malla): la GUI debe
mostrarlo de forma visible, no como texto de barra de estado que se
pierde.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
