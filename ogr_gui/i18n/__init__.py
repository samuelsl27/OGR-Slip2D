# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Internationalization (i18n) manager.

Lightweight in-memory translation system. Dictionaries are loaded at
startup; the user selects the active language via the Preferences dialog
and all ``tr()`` calls pick it up.

Why not use Qt Linguist .ts/.qm files? Because shipping a pure-Python
dict is much simpler for a young project, easier to edit without
compiling, and fully dynamic. We can switch to Qt Linguist later
without touching call-sites (``tr(...)`` signature stays the same).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Callable

_DICTS: dict[str, dict[str, str]] = {
    "en": {},  # English is the reference; keys == values
    "es": {
        # --- v0.1.82: Interpret — Data, Query y leyenda -------------
        # Terminología: «dovela» (slice), «superficie de rotura» (slip
        # surface), «grieta de tracción» (tension crack), «consulta»
        # (query), «línea de empujes» (line of thrust).
        '%d more were discarded before slicing, so they carry no error code and cannot be displayed.': '%d más se descartaron antes del dovelado, así que no llevan código de error y no se pueden mostrar.',
        '%d surface(s) rejected of %d generated:': '%d superficie(s) rechazada(s) de %d generadas:',
        'All data': 'Todos los datos',
        'Data to plot:': 'Datos a representar:',
        'Error code:': 'Código de error:',
        'Factor of Safety Along Slope': 'Factor de seguridad a lo largo del talud',
        'Filter data:': 'Filtrar datos:',
        'Left slope intercept': 'Punto de corte izquierdo con el talud',
        'Minimum value in each bin': 'Valor mínimo en cada intervalo',
        'Number of bins:': 'Número de intervalos:',
        'Right slope intercept': 'Punto de corte derecho con el talud',
        'Select at least one slope intercept.': 'Seleccione al menos un punto de corte con el talud.',
        'Surfaces discarded before slicing are not counted here.': 'Las superficies descartadas antes del dovelado no se cuentan aquí.',
        'Surfaces with error code': 'Superficies con código de error',
        '%d quer(y/ies)': '%d consulta(s)',
        '%d rows copied to the clipboard': '%d filas copiadas al portapapeles',
        '%d surfaces for method %s. A negative value in place of the factor of safety is an error code.': '%d superficies para el método %s. Un valor negativo en lugar del factor de seguridad es un código de error.',
        '0 to 6': '0 a 6',
        'Add Query': 'Añadir consulta',
        'Add Query cancelled': 'Consulta cancelada',
        'Add Result Table (sortable)...': 'Añadir tabla de resultados (ordenable)...',
        'All Surfaces': 'Todas las superficies',
        'All valid surfaces — %d shown': 'Todas las superficies válidas — %d mostradas',
        'Back Analysis...': 'Retroanálisis...',
        'Base inclination': 'Inclinación de la base',
        'Base normal stress': 'Tensión normal en la base',
        'By factor of safety': 'Por factor de seguridad',
        'Copy': 'Copiar',
        'Data': 'Datos',
        'Data:': 'Datos:',
        'Delete Query': 'Eliminar consulta',
        'Delete Query...': 'Eliminar consulta...',
        'Distance along surface': 'Distancia a lo largo de la superficie',
        'Every valid slip surface analysed.': 'Todas las superficies de rotura válidas analizadas.',
        'Export Raw Data': 'Exportar datos brutos',
        'Export Raw Data...': 'Exportar datos brutos...',
        'Export Slice Data (CSV)...': 'Exportar datos de dovelas (CSV)...',
        'Filter Surfaces...': 'Filtrar superficies...',
        'Filter active — %d of %d surfaces shown. The global minimum is always kept.': 'Filtro activo — %d de %d superficies mostradas. El mínimo global se conserva siempre.',
        'Fit to results': 'Ajustar a los resultados',
        'Free Body Diagram of Slice...': 'Diagrama de sólido libre de la dovela...',
        'Global minimum surface': 'Superficie del mínimo global',
        'Graph Query': 'Graficar consulta',
        'Graph Query...': 'Graficar consulta...',
        'Graph SF Along Slope...': 'Graficar FS a lo largo del talud...',
        'Graph SF with Time...': 'Graficar FS con el tiempo...',
        'Horizontal axis:': 'Eje horizontal:',
        'Minimum Surfaces': 'Superficies mínimas',
        'Minimum surface at each grid centre — %d shown': 'Superficie mínima en cada centro de la malla — %d mostradas',
        'Mobilised shear stress': 'Tensión tangencial movilizada',
        'No queries to delete.': 'No hay consultas que eliminar.',
        'No results to export.': 'No hay resultados que exportar.',
        'No results to query.': 'No hay resultados que consultar.',
        'No valid surfaces.': 'No hay superficies válidas.',
        'Number of surfaces:': 'Número de superficies:',
        'Only the N lowest': 'Solo las N más bajas',
        'Pick the surface to query — Esc to cancel': 'Seleccione la superficie a consultar — Esc para cancelar',
        'Query': 'Consulta',
        'Query %d': 'Consulta %d',
        'Query Invalid Surfaces': 'Consultar superficies no válidas',
        'Query Slice Data...': 'Consultar datos de dovela...',
        'Query added — %s': 'Consulta añadida — %s',
        'Restore the default factor-of-safety range: 0 to 6 in 24 intervals of 0.25.': 'Restaurar el rango por defecto del factor de seguridad: 0 a 6 en 24 intervalos de 0,25.',
        'Save...': 'Guardar...',
        'Set the range from the values actually present, once.': 'Fijar el rango a partir de los valores presentes, una sola vez.',
        'Shear strength': 'Resistencia al corte',
        'Show Line of Thrust': 'Mostrar línea de empujes',
        'Show Slices': 'Mostrar dovelas',
        'Show Values Along Surface...': 'Mostrar valores a lo largo de la superficie...',
        'Show the factor of safety, radius and centre in a floating label while picking a query.': 'Mostrar el factor de seguridad, el radio y el centro en una etiqueta flotante al seleccionar una consulta.',
        'Showing %d of %d surfaces.': 'Mostrando %d de %d superficies.',
        'Slice number': 'Número de dovela',
        'Slice weight': 'Peso de la dovela',
        'Summary of Invalid Surfaces...': 'Resumen de superficies no válidas...',
        'Supplemental Contours': 'Isolíneas complementarias',
        'Support Force Analysis...': 'Análisis de la fuerza de soporte...',
        'Surfaces Crossing Point...': 'Superficies que pasan por un punto...',
        'Text during Query': 'Texto durante la consulta',
        'The line of thrust is only defined for methods that resolve the interslice forces (Spencer, GLE/Morgenstern-Price, Lowe-Karafiath, Corps of Engineers).': 'La línea de empujes solo está definida para los métodos que resuelven las fuerzas entre dovelas (Spencer, GLE/Morgenstern-Price, Lowe-Karafiath, Corps of Engineers).',
        'The lowest factor of safety at each slip-centre grid point.': 'El menor factor de seguridad en cada punto de la malla de centros.',
        'The queried surface has no slice data.': 'La superficie consultada no tiene datos de dovelas.',
        'While picking a query, show the error code of centres where no valid surface could be computed.': 'Al seleccionar una consulta, mostrar el código de error de los centros donde no se ha podido calcular ninguna superficie válida.',
        'X coordinate': 'Coordenada X',
        'no valid slip surface at this centre': 'ninguna superficie de rotura válida en este centro',

        # --- v0.1.57: M6 -------------------------------------------
        '(pick a lithology)': '(elija una litología)',
        '(pick a rock mass description)': '(elija una descripción del macizo)',
        '(pick an excavation method)': '(elija un método de excavación)',
        'Calculate mb, s and a from GSI, the intact rock constant mi and the disturbance factor D.': 'Calcular mb, s y a a partir del GSI, la constante de roca intacta mi y el factor de alteración D.',
        'Calculated': 'Calculado',
        'Close Window': 'Cerrar ventana',
        'Disturbance factor D:': 'Factor de alteración D:',
        'GSI and D are judgement-based: use the descriptions above rather than a remembered number. Equations from Hoek, Carranza-Torres and Corkum (2002).': 'El GSI y D dependen del criterio del técnico: use las descripciones de arriba en lugar de un número recordado. Ecuaciones de Hoek, Carranza-Torres y Corkum (2002).',
        'GSI...': 'GSI...',
        'GSI:': 'GSI:',
        'Input': 'Entrada',
        'Parameter Calculator': 'Calculador de parámetros',
        'Untitled': 'Sin título',
        'Use these values': 'Usar estos valores',
        'mi:': 'mi:',

        # --- v0.1.56: menús menores ---------------------------------
        '%d support(s) ungrouped; each can now be edited on its own.': '%d soporte(s) desagrupados; ahora cada uno puede editarse por separado.',
        '%d: %s': '%d: %s',
        'Bitmap': 'Mapa de bits',
        'Both': 'Ambos',
        'Check for Updates...': 'Buscar actualizaciones...',
        'Copy Image will use a bitmap.': 'Copiar imagen usará un mapa de bits.',
        'Copy Image will use vector data, which stays sharp when the figure is enlarged.': 'Copiar imagen usará datos vectoriales, que se mantienen nítidos al ampliar la figura.',
        'Could not read the project: %s': 'No se ha podido leer el proyecto: %s',
        'Could not write the image.': 'No se ha podido escribir la imagen.',
        'Displacement in x:': 'Desplazamiento en x:',
        'Displacement in y:': 'Desplazamiento en y:',
        'Distributed %d: %.3g kPa': 'Distribuida %d: %.3g kPa',
        'Export Image': 'Exportar imagen',
        'Image exported: %d × %d px to %s': 'Imagen exportada: %d × %d px a %s',
        'Import Properties': 'Importar propiedades',
        'Import:': 'Importar:',
        'Imported %d material(s) and %d support type(s). Duplicated names were numbered rather than overwritten.': 'Importados %d material(es) y %d tipo(s) de soporte. Los nombres duplicados se han numerado en lugar de sobrescribirse.',
        'Line %d: %.3g kN/m': 'Lineal %d: %.3g kN/m',
        'Load modified.': 'Carga modificada.',
        'Load:': 'Carga:',
        'Magnitude at the far end:': 'Magnitud en el extremo opuesto:',
        'Modify Load': 'Modificar carga',
        'Modify Load...': 'Modificar carga...',
        'Modify Support': 'Modificar soporte',
        'Modify Support...': 'Modificar soporte...',
        'Move Support': 'Mover soporte',
        'Move Support...': 'Mover soporte...',
        'No support belongs to a pattern. Patterns are created with Add Support Pattern.': 'Ningún soporte pertenece a un patrón. Los patrones se crean con Añadir patrón de soportes.',
        'No support types are defined.': 'No hay tipos de soporte definidos.',
        'Picture Format': 'Formato de imagen',
        'Print Preview...': 'Vista previa de impresión...',
        'Releases are published at opengeorock.org. This command does not contact any server: nothing is sent from your machine.': 'Las versiones se publican en opengeorock.org. Este comando no contacta con ningún servidor: no se envía nada desde su equipo.',
        'Support modified.': 'Soporte modificado.',
        'Support moved by (%.3f, %.3f)': 'Soporte movido (%.3f, %.3f)',
        'Support type:': 'Tipo de soporte:',
        'Support:': 'Soporte:',
        'There are no loads to modify.': 'No hay cargas que modificar.',
        'There are no supports to modify.': 'No hay soportes que modificar.',
        'There are no supports to move.': 'No hay soportes que mover.',
        'There is nothing to export.': 'No hay nada que exportar.',
        'This is OGR Suite %s.': 'Esto es OGR Suite %s.',
        'Ungroup Support Pattern': 'Desagrupar patrón de soportes',
        'Vector (SVG)': 'Vectorial (SVG)',
        'Width in pixels:': 'Anchura en píxeles:',

        # --- v0.1.55: foco, optimización y límites ------------------
        '  [disabled]': '  [desactivado]',
        '%d focus object(s) defined.': '%d objeto(s) de foco definidos.',
        '%d focus object(s) defined. They narrow the search: a circle must satisfy every one of them.': '%d objeto(s) de foco definidos. Acotan la búsqueda: un círculo debe satisfacerlos todos.',
        '%d: %s (%d points, tolerance %.4g)%s': '%d: %s (%d puntos, tolerancia %.4g)%s',
        '(delete all)': '(eliminar todos)',
        'Action:': 'Acción:',
        'Add Focus Line...': 'Añadir línea de foco...',
        'Add Focus Point...': 'Añadir punto de foco...',
        'Add Focus Tangent...': 'Añadir tangente de foco...',
        'Add Focus Window...': 'Añadir ventana de foco...',
        'Add Surface': 'Añadir superficie',
        'Add Surface (centre and radius)...': 'Añadir superficie (centro y radio)...',
        'Capture tolerance:': 'Tolerancia de captura:',
        'Circle added: centre (%.3f, %.3f), radius %.3f': 'Círculo añadido: centro (%.3f, %.3f), radio %.3f',
        'Could not build the search for this method.': 'No se ha podido construir la búsqueda para este método.',
        'Enable / disable': 'Activar / desactivar',
        'Focus Search': 'Búsqueda enfocada',
        'Left limit (x):': 'Límite izquierdo (x):',
        'Manage Focus Objects': 'Gestionar objetos de foco',
        'Manage Focus Objects...': 'Gestionar objetos de foco...',
        'Maximum evaluations:': 'Evaluaciones máximas:',
        'Move Slope Limits': 'Mover límites del talud',
        'Move Slope Limits...': 'Mover límites del talud',
        'No focus objects are defined.': 'No hay objetos de foco definidos.',
        'No improvement found: %s': 'No se ha encontrado mejora: %s',
        'Optimisation applies to NON-CIRCULAR surfaces. The critical surface of this method is a circle; use a Block or Path Search first.': 'La optimización se aplica a superficies NO CIRCULARES. La superficie crítica de este método es un círculo; use antes una búsqueda por bloques o por trayectorias.',
        'Optimised: %s': 'Optimizada: %s',
        'Optimize Surfaces...': 'Optimizar superficies...',
        'Radius:': 'Radio:',
        'Reset Slope Limits': 'Restablecer límites del talud',
        'Right limit (x):': 'Límite derecho (x):',
        'Run an analysis first: optimisation refines an existing surface, so it needs one to start from.': 'Ejecute antes un análisis: la optimización refina una superficie existente, así que necesita una de partida.',
        'Slope Limits': 'Límites del talud',
        'Slope limits reset to automatic.': 'Límites del talud restablecidos a automáticos.',
        'Slope limits: %.3f to %.3f': 'Límites del talud: de %.3f a %.3f',
        'The right limit must be greater than the left one.': 'El límite derecho debe ser mayor que el izquierdo.',
        'This needs %d point(s).': 'Esto necesita %d punto(s).',
        'Toggle or delete:': 'Alternar o eliminar:',

        'Delete': 'Eliminar',
        'Model': 'Modelo',

        # --- v0.1.54: capa de anotación y menú Tools ----------------
        '   |   measured: %.4f': '   |   medido: %.4f',
        '#': '#',
        '%d annotation(s) %s': '%d anotación(es) %s',
        '%d annotation(s) deleted': '%d anotación(es) eliminadas',
        'Add Axes': 'Añadir ejes',
        'Add Image': 'Añadir imagen',
        'Add Image...': 'Añadir imagen...',
        'Added %s': 'Añadido %s',
        'Annotation:': 'Anotación:',
        'Annotations': 'Anotaciones',
        'Annotations are drawn on the model but take no part in the analysis. Use Convert Tool to Boundary to turn one into geometry.': 'Las anotaciones se dibujan sobre el modelo pero no intervienen en el análisis. Use Convertir herramienta en contorno para transformar una en geometría.',
        'Arrow': 'Flecha',
        'Bring to front': 'Traer al frente',
        'Circle': 'Círculo',
        'Convert Tool to Boundary': 'Convertir herramienta en contorno',
        'Convert Tool to Boundary...': 'Convertir herramienta en contorno...',
        'Convert to:': 'Convertir en:',
        'Converted to %s (%d vertices). The annotation was kept.': 'Convertida en %s (%d vértices). La anotación se ha conservado.',
        'Copy style to others': 'Copiar estilo a las demás',
        'Copy to clipboard': 'Copiar al portapapeles',
        "Could not read '%s' as x,y": 'No se ha podido leer «%s» como x,y',
        'Delete All Annotations': 'Eliminar todas las anotaciones',
        'Delete all %d annotation(s)? The physical model is not affected.': '¿Eliminar las %d anotación(es)? El modelo físico no se ve afectado.',
        'Dimension X': 'Cota X',
        'Dimension Y': 'Cota Y',
        'Dimensions': 'Cotas',
        'Draw': 'Dibujar',
        'Enter %d point(s) as x,y  x,y ...': 'Introduzca %d punto(s) como x,y  x,y ...',
        'Head': 'Cabeza',
        'Hide All Annotations': 'Ocultar todas las anotaciones',
        'Hydraulic Properties Table': 'Tabla de propiedades hidráulicas',
        'Image placed over the model extent; use Manage Annotations to reposition it.': 'Imagen colocada sobre la extensión del modelo; use Gestionar anotaciones para recolocarla.',
        'K1 angle': 'Ángulo de K1',
        'Line': 'Línea',
        'Manage Annotations...': 'Gestionar anotaciones...',
        'No annotation can become geometry. Dimensions, text and axes annotate the model rather than define it; draw a line, polyline, polygon, rectangle or circle first.': 'Ninguna anotación puede convertirse en geometría. Las cotas, el texto y los ejes anotan el modelo en lugar de definirlo; dibuje antes una línea, polilínea, polígono, rectángulo o círculo.',
        'No material has hydraulic properties. Define them in Groundwater → Define Hydraulic Properties.': 'Ningún material tiene propiedades hidráulicas. Defínalas en Agua subterránea → Definir propiedades hidráulicas.',
        'No materials are defined.': 'No hay materiales definidos.',
        'No supports are defined.': 'No hay soportes definidos.',
        'Nothing to show.': 'Nada que mostrar.',
        'Points': 'Puntos',
        'Polygon': 'Polígono',
        'Polyline': 'Polilínea',
        'Property Tables': 'Tablas de propiedades',
        'Read-only: edit in the dedicated dialogs, where the validation lives. Click a column header to sort and compare.': 'Solo lectura: edite en los diálogos específicos, donde está la validación. Pulse una cabecera de columna para ordenar y comparar.',
        'Rectangle': 'Rectángulo',
        'Saturated': 'Saturado',
        'Saturated water content': 'Contenido de agua saturado',
        'Send to back': 'Enviar al fondo',
        'Show All Annotations': 'Mostrar todas las anotaciones',
        'Specific storage': 'Almacenamiento específico',
        'Strength model': 'Modelo de resistencia',
        'Support Properties Table': 'Tabla de propiedades de soportes',
        'Tail': 'Cola',
        'Text': 'Texto',
        'Text:': 'Texto:',
        'There are no annotations.': 'No hay anotaciones.',
        'This annotation has no usable geometry.': 'Esta anotación no tiene geometría utilizable.',
        'This shape needs %d point(s).': 'Esta forma necesita %d punto(s).',
        'Toggle visible': 'Alternar visibilidad',
        'Unit weight': 'Peso específico',
        'Visible': 'Visible',
        'Z': 'Z',
        'hidden': 'ocultas',
        'shown': 'mostradas',

        'Percent of variable range (%)': 'Porcentaje del rango de la variable (%)',
        'User data computed for %d nodes: range %.4f to %.4f': 'Datos de usuario calculados para %d nodos: rango de %.4f a %.4f',

        # --- v0.1.53: menús completos de Interpret ------------------
        '%d distinct global minimum surface(s)': '%d superficie(s) de mínimo global distintas',
        '%d query point(s)': '%d punto(s) de consulta',
        '%d surface(s) rejected of %d evaluated:': '%d superficie(s) rechazadas de %d evaluadas:',
        '%d: circle centre (%.2f, %.2f) r = %.2f': '%d: círculo centro (%.2f, %.2f) r = %.2f',
        '%d: non-circular surface': '%d: superficie no circular',
        '(all)': '(todas)',
        'Add Query': 'Añadir consulta',
        'At (%.3f, %.3f)': 'En (%.3f, %.3f)',
        'Back Analysis': 'Retroanálisis',
        'Back analysis is only available for Bishop, Janbu and Janbu Corrected, and the force must have a moment arm.': 'El retroanálisis solo está disponible para Bishop, Janbu y Janbu Corregido, y la fuerza debe tener brazo de momento.',
        'Convergence': 'Convergencia',
        'Could not write the file: %s': 'No se ha podido escribir el archivo: %s',
        'Critical probabilistic surface: PF = %.2f %%, reliability index = %.3f': 'Superficie probabilística crítica: PF = %.2f %%, índice de fiabilidad = %.3f',
        'Define User Data': 'Definir datos de usuario',
        'Delete Query': 'Eliminar consulta',
        'Elevation of the force:': 'Cota de la fuerza:',
        'Enter two numbers: x,y': 'Introduzca dos números: x,y',
        'Every surface evaluated successfully.': 'Todas las superficies se evaluaron correctamente.',
        'Export All Nodal Values...': 'Exportar todos los valores nodales...',
        'Export Statistics Data...': 'Exportar datos estadísticos...',
        'Exported %d nodes to %s': 'Exportados %d nodos a %s',
        'Expression using H (total head), P (pressure head) and u (pore pressure), for example  H - 25': 'Expresión con H (cabeza total), P (cabeza de presión) y u (presión intersticial), por ejemplo  H - 25',
        'Factor of safety at query points': 'Factor de seguridad en los puntos de consulta',
        'Global minima found:': 'Mínimos globales encontrados:',
        'Groundwater Query': 'Consulta de agua subterránea',
        'Iteration': 'Iteración',
        'Iteration history': 'Historial de iteraciones',
        'Iterations: %d': 'Iteraciones: %d',
        'Maximum change': 'Cambio máximo',
        'No critical probabilistic surface: it comes from the Overall Slope analysis type.': 'Sin superficie probabilística crítica: proviene del tipo de análisis Talud completo.',
        'No critical surface with slice data.': 'Sin superficie crítica con datos de dovelas.',
        'No critical surface.': 'Sin superficie crítica.',
        'No per-iteration history was recorded for this run.': 'No se registró historial por iteración en esta corrida.',
        'No probabilistic result.': 'Sin resultado probabilístico.',
        'No query points to delete.': 'No hay puntos de consulta que eliminar.',
        'No query points. Use Add Query first.': 'No hay puntos de consulta. Use Añadir consulta primero.',
        "No stage has a computed factor of safety. Tick 'Calculate SF' on the stages you need and recompute.": 'Ninguna etapa tiene factor de seguridad calculado. Marque «Calcular FS» en las etapas que necesite y recalcule.',
        'No surface passes near the query points.': 'Ninguna superficie pasa cerca de los puntos de consulta.',
        'Number of samples': 'Número de muestras',
        'Overlay iso-lines of the contoured field on top of the filled bands.': 'Superponer isolíneas del campo de contornos sobre las bandas rellenas.',
        'Pick GM Surfaces': 'Elegir superficies de mínimo global',
        'Point as x,y:': 'Punto como x,y:',
        'Query point': 'Punto de consulta',
        'Remove:': 'Quitar:',
        'Required support force for FS = %g': 'Fuerza de soporte requerida para FS = %g',
        'Requires a computed groundwater analysis.': 'Requiere un análisis de agua subterránea calculado.',
        'Requires a probabilistic or sensitivity analysis: run Statistics → Compute Statistics in the modeller.': 'Requiere un análisis probabilístico o de sensibilidad: ejecute Estadística → Calcular estadística en el modelador.',
        'Requires a transient groundwater analysis with per-stage factors of safety.': 'Requiere un análisis de agua subterránea transitorio con factores de seguridad por etapa.',
        'Requires at least one support in the model.': 'Requiere al menos un soporte en el modelo.',
        'Residual': 'Residuo',
        'Sensitivity': 'Sensibilidad',
        'Statistics exported to %s': 'Estadística exportada a %s',
        'Supports on the critical surface (FS = %.4f):': 'Soportes en la superficie crítica (FS = %.4f):',
        'The expression could not be evaluated: %s': 'No se ha podido evaluar la expresión: %s',
        'The passive value is the larger and therefore the conservative one for design.': 'El valor pasivo es el mayor y por tanto el conservador para diseño.',
        'The point lies outside the mesh.': 'El punto queda fuera de la malla.',
        'This run recorded no convergence history. The seepage solver reports its iteration count and final state instead: %d iterations, converged = %s.': 'Esta corrida no registró historial de convergencia. El solver de filtración informa en su lugar del número de iteraciones y el estado final: %d iteraciones, convergido = %s.',
        'This run recorded no separate global minima. They are produced by the Overall Slope analysis type, which repeats the whole search per sample.': 'Esta corrida no registró mínimos globales separados. Los produce el tipo de análisis Talud completo, que repite toda la búsqueda por muestra.',
        'Time': 'Tiempo',
        'Total head: %.4f': 'Cabeza total: %.4f',
        'Value': 'Valor',
        # v0.1.87 — panel de datos de dovela (Query Slice Data)
        'Slice Data': 'Datos de la dovela',
        'Property': 'Propiedad',
        'Click on any slice to view its properties (Esc to exit).':
            'Pulsa sobre una dovela para ver sus propiedades (Esc para '
            'salir).',
        'Click was outside the slice range.':
            'La pulsación cayó fuera del rango de dovelas.',
        'Slice %d of %d — x from %.2f to %.2f':
            'Dovela %d de %d — x de %.2f a %.2f',
        '─ Geometry ─': '─ Geometría ─',
        '─ Forces ─': '─ Fuerzas ─',
        '─ Stresses ─': '─ Tensiones ─',
        '─ Material ─': '─ Material ─',
        'Slice Number': 'Número de dovela',
        'X centre (m)': 'X del centro (m)',
        'Width b (m)': 'Ancho b (m)',
        'Base length l (m)': 'Longitud de base l (m)',
        'Base angle α (°)': 'Ángulo de base α (°)',
        'Height h (m)': 'Altura h (m)',
        'Base y left (m)': 'y de base izquierda (m)',
        'Base y right (m)': 'y de base derecha (m)',
        'Weight W (kN)': 'Peso W (kN)',
        'Pore pressure u (kPa)': 'Presión intersticial u (kPa)',
        'Surface load q (kPa)': 'Carga en superficie q (kPa)',
        'Base normal force N (kN)': 'Fuerza normal en la base N (kN)',
        'Driving shear W·sinα (kN)': 'Cortante motor W·senα (kN)',
        'Base normal stress σₙ (kPa)': 'Tensión normal en la base σₙ (kPa)',
        'Effective normal σ′ₙ (kPa)': 'Normal efectiva σ′ₙ (kPa)',
        'Shear strength τ_f (kPa)': 'Resistencia al corte τ_f (kPa)',
        'Mobilised shear τ_m = τ_f/F (kPa)':
            'Cortante movilizado τ_m = τ_f/F (kPa)',
        'Material': 'Material',
        'Strength model': 'Modelo de resistencia',
        'Unit weight γ (kN/m³)': 'Peso específico γ (kN/m³)',
        'Base cohesion c (kPa)': 'Cohesión en la base c (kPa)',
        'Base friction angle φ (°)':
            'Ángulo de rozamiento en la base φ (°)',
        'active: %.2f': 'activa: %.2f',
        'capacity %.2f kN': 'capacidad %.2f kN',
        'capacity not defined': 'capacidad no definida',
        'converged: %s': 'convergido: %s',
        'did not converge': 'no convergió',
        'mean FoS': 'FoS medio',
        'no': 'no',
        'passive: %.2f': 'pasiva: %.2f',
        'pressure head: %.4f': 'cabeza de presión: %.4f',
        'probability of failure (%)': 'probabilidad de fallo (%)',
        'total head: %.4f': 'cabeza total: %.4f',
        'yes': 'sí',

        'Auto': 'Auto',
        'Advanced groundwater options are mutually exclusive: enabling this switches off Excess Pore Pressure and Rapid Drawdown.': 'Las opciones avanzadas de agua subterránea son mutuamente excluyentes: activar esta desactiva Exceso de presión intersticial y Desembalse rápido.',
        'Global Minimum reuses the deterministic critical surface for every sample. Overall Slope repeats the WHOLE search per sample: more rational, substantially slower.': 'Mínimo global reutiliza la superficie crítica determinista en cada muestra. Talud completo repite TODA la búsqueda por muestra: más racional, notablemente más lento.',
        'Latin Hypercube converges markedly faster: around 1000 of its samples match some 5000 Monte Carlo ones.': 'El hipercubo latino converge mucho más rápido: unas 1000 de sus muestras equivalen a unas 5000 de Monte Carlo.',
        'Number of equal intervals each variable range is divided into for the sensitivity sweep.': 'Número de intervalos iguales en que se divide el rango de cada variable para el barrido de sensibilidad.',
        'Number of time steps per stage. Auto derives it from the element size and the storage, so the water front cannot cross more than about one element per step.': 'Número de pasos de tiempo por etapa. Auto lo deduce del tamaño de elemento y del almacenamiento, de forma que el frente de agua no pueda cruzar más de un elemento por paso.',
        'Rejects a surface with tension on a slice base. Applied AFTER the factor of safety converges, over a percentage of slices measured from the toe.': 'Rechaza una superficie con tracción en la base de una dovela. Se aplica DESPUÉS de converger el factor de seguridad, sobre un porcentaje de dovelas contado desde el pie.',
        'Search range for the interslice force scaling factor used by Spencer and GLE / Morgenstern-Price.': 'Rango de búsqueda del factor de escala de las fuerzas interdovela que usan Spencer y GLE / Morgenstern-Price.',

        # --- v0.1.52: páginas nuevas de Project Settings ------------
        '%d stage(s), %d with a factor of safety': '%d etapa(s), %d con factor de seguridad',
        'A pseudo-random stream is reproducible: the same seed gives the same answer, which is what makes a probabilistic result defensible in a report and comparable between runs. A random stream is seeded from the clock, so successive runs explore differently — useful to check that a conclusion is not an artefact of one seed.': 'Un flujo pseudoaleatorio es reproducible: la misma semilla da la misma respuesta, que es lo que hace defendible un resultado probabilístico en un informe y comparable entre corridas. Un flujo aleatorio toma la semilla del reloj, así que corridas sucesivas exploran de forma distinta — útil para comprobar que una conclusión no es un artefacto de una semilla concreta.',
        'Accelerate convergence (Steffensen)': 'Acelerar convergencia (Steffensen)',
        'Analysis type:': 'Tipo de análisis:',
        'Apply partial factors': 'Aplicar coeficientes parciales',
        'Cohesion:': 'Cohesión:',
        'Custom': 'Personalizado',
        'Design Standard': 'Norma de diseño',
        'Design standard:': 'Norma de diseño:',
        'Eurocode 7 — DA1 Combination 1': 'Eurocódigo 7 — DA1 Combinación 1',
        'Eurocode 7 — DA1 Combination 2': 'Eurocódigo 7 — DA1 Combinación 2',
        'Eurocode 7 — DA2': 'Eurocódigo 7 — DA2',
        'Eurocode 7 — DA3': 'Eurocódigo 7 — DA3',
        'Generation:': 'Generación:',
        'Global Minimum': 'Mínimo global',
        'Initial factor of safety:': 'Factor de seguridad inicial:',
        'Latin Hypercube': 'Hipercubo latino',
        'Maximum lambda:': 'Lambda máxima:',
        'Minimum lambda:': 'Lambda mínima:',
        'Monte Carlo': 'Monte Carlo',
        'Number of samples:': 'Número de muestras:',
        'Off by default: applying partial factors silently would change every factor of safety previously compared against, so it has to be an explicit choice. Selecting a standard loads its factors; choose Custom to enter your own.': 'Desactivado por defecto: aplicar coeficientes parciales en silencio cambiaría todos los factores de seguridad con los que se haya comparado antes, así que debe ser una elección explícita. Elegir una norma carga sus coeficientes; escoja Personalizado para introducir los suyos.',
        'Overall Slope': 'Talud completo',
        'Permanent actions:': 'Acciones permanentes:',
        'Probabilistic analysis': 'Análisis probabilístico',
        'Pseudo-random': 'Pseudoaleatorio',
        'Random': 'Aleatorio',
        'Random Numbers': 'Números aleatorios',
        'Random variables are defined in Statistics → Random Variables.': 'Las variables aleatorias se definen en Estadística → Variables aleatorias.',
        'Resistance:': 'Resistencia:',
        'Sampling method:': 'Método de muestreo:',
        'Seed:': 'Semilla:',
        'Sensitivity analysis': 'Análisis de sensibilidad',
        'Sensitivity intervals:': 'Intervalos de sensibilidad:',
        "Stage times and the per-stage 'Calculate SF' flags are edited in Groundwater → Transient Groundwater, next to the boundary conditions they depend on.": 'Los tiempos de etapa y las casillas «Calcular FS» por etapa se editan en Agua subterránea → Agua subterránea transitoria, junto a las condiciones de contorno de las que dependen.',
        'Stages defined:': 'Etapas definidas:',
        'Tensile stress check': 'Comprobación de tracción',
        'The m-alpha check is deliberately NOT offered here. It rejects surfaces whose base normal denominator falls below 0.2, and measurement showed it also rejects the reference-validated critical circle, so it is a diagnostic rather than a validity criterion and stays with the search options.': 'La comprobación de m-alpha NO se ofrece aquí a propósito. Rechaza superficies cuyo denominador de la normal en la base baja de 0.2, y se midió que también rechaza el círculo crítico validado contra la referencia, así que es un diagnóstico y no un criterio de validez, y permanece en las opciones de búsqueda.',
        'Transient': 'Transitorio',
        'Unit weight:': 'Peso específico:',
        'Variable actions:': 'Acciones variables:',
        'tan(friction angle):': 'tan(ángulo de rozamiento):',

        # --- v0.1.51: data tips y diálogo de forzado ----------------
        'Capture tolerances': 'Tolerancias de captura',
        'Constraints': 'Restricciones',
        'DATA TIPS': 'DATOS',
        'Data tips': 'Datos al pasar el cursor',
        'Extension:': 'Extensión:',
        'Grid node:': 'Nodo de rejilla:',
        'Grid snap (F9)': 'Forzar a rejilla (F9)',
        'Grid spacing': 'Espaciado de rejilla',
        'Horizontal:': 'Horizontal:',
        "Hovering over a material, support or load shows its properties. 'Minimum' shows only the identity, enough to tell two objects apart while drawing.": 'Al pasar el cursor sobre un material, soporte o carga se muestran sus propiedades. «Mínimo» muestra solo la identidad, bastante para distinguir dos objetos mientras se dibuja.',
        'Line:': 'Línea:',
        'Object snap (F3)': 'Forzar a objeto (F3)',
        'Orthogonal (F8)': 'Ortogonal (F8)',
        'Orthogonal locks the movement to an axis when the cursor is within this angle of horizontal or vertical.': 'El modo ortogonal fija el movimiento a un eje cuando el cursor está dentro de este ángulo respecto a la horizontal o la vertical.',
        'Orthogonal window:': 'Ventana ortogonal:',
        'Snap...': 'Forzado...',
        'Tolerances are in SCREEN PIXELS. The canvas converts them to model units, which is what keeps snapping equally easy at any zoom; a tolerance in metres would get harder to use the further you zoomed out.': 'Las tolerancias van en PÍXELES DE PANTALLA. El lienzo las convierte a unidades del modelo, que es lo que mantiene el forzado igual de cómodo a cualquier zoom; una tolerancia en metros sería más difícil de usar cuanto más se alejara la vista.',
        'Vertex:': 'Vértice:',
        'Vertical:': 'Vertical:',
        'off': 'desactivado',
        'on': 'activado',

        # --- v0.1.50: motor de contornos ----------------------------
        'Automatic range from the results': 'Rango automático a partir de los resultados',
        'Contour Options': 'Opciones de contorno',
        'Contour Options...': 'Opciones de contorno...',
        'Filled': 'Relleno',
        'Filled (with lines)': 'Relleno con líneas',
        'Interval size:': 'Tamaño del intervalo:',
        'Left on, the range follows the data as results change. The upper bound uses a percentile so a single extreme value cannot squash everything else into one band.': 'Activado, el rango sigue a los datos según cambian los resultados. El límite superior usa un percentil para que un único valor extremo no aplaste todo lo demás en una sola banda.',
        'Lines': 'Líneas',
        'Maximum:': 'Máximo:',
        'Minimum:': 'Mínimo:',
        'Number format': 'Formato numérico',
        'Off': 'Desactivado',
        'Palette:': 'Paleta:',
        'Pore pressure': 'Presión intersticial',
        'Pressure head': 'Cabeza de presión',
        'Preview:': 'Vista previa:',
        'Range': 'Rango',
        'Reverse colours': 'Invertir colores',
        'Scalar field': 'Campo escalar',
        'Show:': 'Mostrar:',
        'Smooth gradient': 'Degradado continuo',
        'Total head': 'Cabeza total',

        'Data Tips': 'Datos al pasar el cursor',
        'None': 'Ninguno',

        # --- v0.1.49: leyenda e indicadores de Interpret -------------
        '   |   FS = %s': '   |   FS = %s',
        'Click to toggle %s': 'Clic para alternar %s',
        'Decimal places:': 'Decimales:',
        'Factor of safety': 'Factor de seguridad',
        'Legend': 'Leyenda',
        'Legend Options': 'Opciones de leyenda',
        'Legend Options...': 'Opciones de leyenda...',
        'Maximum': 'Máximo',
        'Method: %s': 'Método: %s',
        'Minimum': 'Mínimo',
        'Number of intervals:': 'Número de intervalos:',
        'Scientific notation': 'Notación científica',
        'Show Legend': 'Mostrar leyenda',

        # --- v0.1.48: exportación DXF -------------------------------
        'Annotations (title, factor of safety)': 'Anotaciones (título, factor de seguridad)',
        'Appearance': 'Aspecto',
        'Boundaries (geometry)': 'Contornos (geometría)',
        'Contents': 'Contenido',
        'Critical slip surface': 'Superficie de rotura crítica',
        'Export': 'Exportar',
        'Export DXF': 'Exportar DXF',
        'Exported to %s   |   %s': 'Exportado a %s   |   %s',
        'Finite element mesh': 'Malla de elementos finitos',
        'Length of the load arrows, as a percentage of the model diagonal, so they stay legible at any model size.': 'Longitud de las flechas de carga, como porcentaje de la diagonal del modelo, para que sigan siendo legibles a cualquier escala.',
        'Load arrow size:': 'Tamaño de las flechas de carga:',
        'Loads (as arrows)': 'Cargas (como flechas)',
        'Model geometry is written to the layers the importer recognises (%s), so the drawing can be edited in CAD and imported back. Results — loads, mesh, slip surface and annotations — go to separate OGR_X_ layers that the importer ignores, so re-importing cannot turn a load arrow into a material boundary.': 'La geometría del modelo se escribe en las capas que reconoce el importador (%s), de modo que el dibujo puede editarse en CAD y volver a importarse. Los resultados —cargas, malla, superficie de rotura y anotaciones— van a capas OGR_X_ aparte que el importador ignora, así que reimportar no puede convertir una flecha de carga en un contorno de material.',
        'Off by default: a mesh writes one line per element edge, which can be thousands of entities.': 'Desactivado por defecto: una malla escribe una línea por arista de elemento, lo que pueden ser miles de entidades.',
        'The drawing could not be written.': 'No se ha podido escribir el dibujo.',
        'The model is in metres; coordinates are converted to this unit and recorded in the file header.': 'El modelo está en metros; las coordenadas se convierten a esta unidad y se registran en el encabezado del archivo.',
        'Write coordinates in:': 'Escribir coordenadas en:',
        'skipped: %s': 'omitido: %s',

        # --- v0.1.47: informe de problemas DXF ----------------------
        '%d problem(s) found (%d error(s)). The geometry has been imported anyway: select a problem to locate it and correct it in the editor.': '%d problema(s) encontrados (%d error(es)). La geometría se ha importado igualmente: seleccione un problema para localizarlo y corregirlo en el editor.',
        '%s — %s (%d)': '%s — %s (%d)',
        'A material boundary ends without touching anything, so its region will not close. Either extend it in the editor until it meets another boundary, or re-import with a larger welding tolerance.': 'Un contorno de material termina sin tocar nada, así que su región no cerrará. Prolónguelo en el editor hasta encontrar otro contorno, o vuelva a importar con una tolerancia de soldadura mayor.',
        'DXF Import — Problems': 'Importación DXF — Problemas',
        'Error': 'Error',
        'Go to problem': 'Ir al problema',
        'Increase the welding tolerance and import again. If the areas still disagree, look for a boundary that crosses another without sharing a node, or one that stops just short of the external boundary.': 'Aumente la tolerancia de soldadura y vuelva a importar. Si las áreas siguen sin cuadrar, busque un contorno que cruce a otro sin compartir nodo, o uno que se quede justo antes del contorno externo.',
        'Location': 'Ubicación',
        'No geometry was assigned to any layer.': 'No se asignó geometría a ninguna capa.',
        'No layer was mapped to the external boundary. Re-run the import and assign one in the layer table: without it the model cannot define regions at all.': 'Ninguna capa se asignó al contorno externo. Repita la importación y asigne una en la tabla de capas: sin él el modelo no puede definir regiones.',
        'No problems: the imported geometry closes correctly.': 'Sin problemas: la geometría importada cierra correctamente.',
        'Note': 'Nota',
        'Problem': 'Problema',
        "Several closed shapes were mapped to the external boundary. The largest was kept. If the wrong one was chosen, map the others to 'Material Boundary' instead.": "Se asignaron varias formas cerradas al contorno externo. Se ha conservado la mayor. Si no era la correcta, asigne las demás a 'Contorno de material'.",
        'The external boundary arrived open and was closed with a straight segment. Check that the added segment follows the intended ground surface; if not, close the outline in the CAD drawing and import again.': 'El contorno externo llegó abierto y se ha cerrado con un segmento recto. Compruebe que el segmento añadido sigue la superficie del terreno prevista; si no, cierre el contorno en el dibujo CAD y vuelva a importar.',
        'The external boundary does not have enough vertices to enclose an area.': 'El contorno externo no tiene vértices suficientes para encerrar un área.',
        'The regions could not be built from the imported geometry. This usually means boundaries cross without sharing a node; try a larger welding tolerance.': 'No se han podido construir las regiones con la geometría importada. Suele deberse a contornos que se cruzan sin compartir nodo; pruebe una tolerancia de soldadura mayor.',
        'Warning': 'Aviso',
        'Zoom all': 'Ver todo',

        'Number of factors of safety compared\nbefore stopping:': 'Número de factores de seguridad comparados\nantes de parar:',

        # --- v0.1.46: importación DXF -------------------------------
        '%d problem(s) reported': '%d problema(s) reportados',
        '%d region(s)': '%d región(es)',
        '(ignore)': '(ignorar)',
        'Curve discretisation:': 'Discretización de curvas:',
        'Douglas-Peucker tolerance, also as a percentage of the model diagonal. Vertices shared with another boundary are never removed.': 'Tolerancia Douglas-Peucker, también como porcentaje de la diagonal del modelo. Los vértices compartidos con otro contorno nunca se eliminan.',
        'Drawdown Line': 'Línea de desembalse',
        'Drawing units:': 'Unidades del dibujo:',
        'Endpoints closer than this are welded together and a node is inserted where one lands on the interior of a segment. Measured as a percentage of the model diagonal, so the same value works whatever the drawing units.': 'Los extremos más cercanos que este valor se sueldan, insertando un nodo cuando uno cae en el interior de un segmento. Se mide como porcentaje de la diagonal del modelo, así que el mismo valor sirve cualquiera que sea la unidad del dibujo.',
        'Entities': 'Entidades',
        'Geometry repair': 'Reparación de geometría',
        'Import': 'Importar',
        'Import DXF': 'Importar DXF',
        'Import as': 'Importar como',
        'Imported %s': 'Importado %s',
        'Layer': 'Capa',
        'Layers found in the drawing:': 'Capas encontradas en el dibujo:',
        'No problems found.': 'No se han encontrado problemas.',
        'Press Preview to check the geometry before importing.': 'Pulse Vista previa para comprobar la geometría antes de importar.',
        'Preview': 'Vista previa',
        'Preview failed.': 'La vista previa ha fallado.',
        'REGION AREAS DO NOT MATCH (%.2f vs %.2f): some region did not close. Try a larger welding tolerance.': 'LAS ÁREAS NO COINCIDEN (%.2f frente a %.2f): alguna región no ha cerrado. Pruebe una tolerancia de soldadura mayor.',
        'Reading': 'Lectura',
        'Recommended: %.3f – %.3f %% of the model diagonal': 'Recomendado: %.3f – %.3f %% de la diagonal del modelo',
        'Replace existing boundaries of the imported types': 'Sustituir los contornos existentes de los tipos importados',
        'Segments per full circle used to discretise arcs, circles, splines and polyline bulges. An arc receives its proportional share.': 'Segmentos por círculo completo para discretizar arcos, círculos, splines y bulges de polilínea. Un arco recibe su parte proporcional.',
        'Simplification tolerance:': 'Tolerancia de simplificación:',
        'Simplify polylines': 'Simplificar polilíneas',
        'The drawing could not be read.': 'No se ha podido leer el dibujo.',
        "The file suggests '%s'; it is only a hint and is often missing or wrong, so check it.": "El archivo sugiere '%s'; es solo una indicación, a menudo ausente o incorrecta, así que compruébela.",
        'Vertices': 'Vértices',
        'Vertices: %d → %d': 'Vértices: %d → %d',
        'WARNING: region areas do not match the external boundary; some region did not close.': 'AVISO: las áreas de las regiones no coinciden con el contorno externo; alguna región no ha cerrado.',
        'Welding tolerance:': 'Tolerancia de soldadura:',
        'crossings split: %d': 'cruces partidos: %d',
        'nothing': 'nada',
        'region areas match the external boundary — geometry closes': 'las áreas de las regiones coinciden con el contorno externo — la geometría cierra',
        'regions: %d': 'regiones: %d',
        'welded: %d (%d nodes inserted)': 'soldados: %d (%d nodos insertados)',

        'Assign Material': 'Asignar material',

        # --- v0.1.42: menús nuevos ----------------------------------
        'Groundwater': 'Agua subterránea',
        'Statistics': 'Estadística',

        # --- v0.1.41: claves preexistentes sin traducir --------------
        '(no parameters)': '(sin parámetros)',
        '+ Add row': '+ Añadir fila',
        'Add Support Pattern': 'Añadir patrón de soportes',
        'Add row': 'Añadir fila',
        'Air Entry Value': 'Valor de entrada de aire',
        'Allow suction (keep u < 0)': 'Permitir succión (conservar u < 0)',
        'Angle from horizontal:': 'Ángulo desde la horizontal:',
        'Application:': 'Aplicación:',
        'Apply to:': 'Aplicar a:',
        'Assign': 'Asignar',
        'Boundary condition': 'Condición de contorno',
        'Capacity vs Distance from Head (points)': 'Capacidad frente a distancia a la cabeza (puntos)',
        'Clear': 'Limpiar',
        'Color:': 'Color:',
        'Default to compressed format when saving': 'Guardar en formato comprimido por defecto',
        'Define Support Properties': 'Definir propiedades de soporte',
        'Delete selected': 'Eliminar lo seleccionado',
        'Discharge section…': 'Sección de descarga…',
        'Duplicate': 'Duplicar',
        'Export Data (CSV)...': 'Exportar datos (CSV)...',
        'Export Image...': 'Exportar imagen...',
        'Factor of safety vs time': 'Factor de seguridad frente al tiempo',
        'Field:': 'Campo:',
        'Flip angle 180°': 'Invertir ángulo 180°',
        'FoS vs time…': 'FoS frente al tiempo…',
        'Force': 'Fuerza',
        'Force Application:': 'Aplicación de la fuerza:',
        'Force Orientation:': 'Orientación de la fuerza:',
        'Force application': 'Aplicación de la fuerza',
        'Force direction:': 'Dirección de la fuerza:',
        'Free surface (P=0)': 'Superficie freática (P=0)',
        'Generate Report': 'Generar informe',
        'Geometry': 'Geometría',
        'Grid type:': 'Tipo de malla:',
        'Head (x, y):': 'Cabeza (x, y):',
        'IDW neighbours:': 'Vecinos IDW:',
        'Import CSV…': 'Importar CSV…',
        'In-plane spacing:': 'Separación en el plano:',
        'Interpolation:': 'Interpolación:',
        'Interpret Groundwater — OGR FEM2D': 'Interpretar agua subterránea — OGR FEM2D',
        'Keep head positions (only adjust length / angle)': 'Mantener las posiciones de cabeza (ajustar solo longitud / ángulo)',
        'Length:': 'Longitud:',
        'Load Demo Slope': 'Cargar talud de ejemplo',
        'Mark file as modified after importing': 'Marcar el archivo como modificado tras importar',
        'Mesh': 'Malla',
        'Mode:': 'Modo:',
        'Modify Support Pattern': 'Modificar patrón de soportes',
        'Name:': 'Nombre:',
        'No results yet.': 'Todavía no hay resultados.',
        'No seepage result.': 'Sin resultado de filtración.',
        'Orientation along boundary': 'Orientación a lo largo del contorno',
        'Pick by:': 'Seleccionar por:',
        'Restore defaults': 'Restaurar valores por defecto',
        'Seepage face': 'Cara de rezume',
        'Set Boundary Conditions': 'Definir condiciones de contorno',
        'Show Tabs for Multiple Windows': 'Mostrar pestañas para varias ventanas',
        'Stage:': 'Etapa:',
        'Support Properties': 'Propiedades del soporte',
        'Support Type:': 'Tipo de soporte:',
        'Support Types': 'Tipos de soporte',
        'Support type': 'Tipo de soporte',
        'Tail (x, y):': 'Cola (x, y):',
        'Unsaturated Shear Strength Angle': 'Ángulo de resistencia al corte no saturada',
        'User Angle (from horizontal):': 'Ángulo de usuario (desde la horizontal):',
        'User Angle:': 'Ángulo de usuario:',
        'Value:': 'Valor:',
        'Vertex Coordinate Table': 'Tabla de coordenadas de vértices',
        'Water Pressure Grid': 'Malla de presiones de agua',
        'Zoom': 'Zoom',
        '− Remove row': '− Quitar fila',

        # --- v0.1.41: cobertura ampliada de la interfaz -------------
        '  Method:  ': '  Método:  ',
        '+ Add': '+ Añadir',
        '+ Row': '+ Fila',
        '<i>No material selected</i>': '<i>Ningún material seleccionado</i>',
        '<i>No results to display.</i>': '<i>No hay resultados que mostrar.</i>',
        '<i>Positive = expand outward. Negative = shrink inward.</i>': '<i>Positivo = expandir hacia fuera. Negativo = contraer hacia dentro.</i>',
        'A:': 'A:',
        'Actual range:': 'Rango real:',
        'Add Drawdown Line': 'Añadir línea de desembalse',
        'Add Grid': 'Añadir malla',
        'Add Row': 'Añadir fila',
        'Add a Block Search object (search window) on the model': 'Añadir un objeto de búsqueda por bloques (ventana de búsqueda) al modelo',
        'Add stage': 'Añadir etapa',
        'Add →': 'Añadir →',
        'Advanced': 'Avanzado',
        'Analysis method:': 'Método de análisis:',
        'Analysis:': 'Análisis:',
        'Angle (CCW):': 'Ángulo (antihorario):',
        'Angle:': 'Ángulo:',
        'Apply seismic load to compute': 'Aplicar carga sísmica al cálculo',
        'Assign Material': 'Asignar material',
        'Author:': 'Autor:',
        'Auto Hu (compute from water-surface slope)': 'Hu automático (calculado de la pendiente de la superficie de agua)',
        'Auto Refine Search Options': 'Opciones de búsqueda de refinado automático',
        'Auto-generate the slip-circle search grid': 'Generar automáticamente la malla de búsqueda de círculos',
        'Available parameters': 'Parámetros disponibles',
        'B:': 'B:',
        'Back Analysis of Support Force': 'Retroanálisis de la fuerza de soporte',
        'Basic': 'Básico',
        'Bins:': 'Intervalos:',
        'Block Search Options': 'Opciones de búsqueda por bloques',
        'Boundaries': 'Contornos',
        'Boundary Condition Values': 'Valores de condiciones de contorno',
        'Boundary Conditions': 'Condiciones de contorno',
        'Bubbling pressure:': 'Presión de burbujeo:',
        'C:': 'C:',
        'Calculate Excess Pore Pressure (B-bar method)': 'Calcular exceso de presión intersticial (método B-bar)',
        'Cancel': 'Cancelar',
        'Capture as initial state': 'Capturar como estado inicial',
        'Capture current BCs': 'Capturar condiciones actuales',
        'Change Slope Angle': 'Cambiar ángulo del talud',
        'Circles per division:': 'Círculos por división:',
        'Close': 'Cerrar',
        'Coefficient in temperature reduction:': 'Coeficiente de reducción de temperatura:',
        'Comments:': 'Comentarios:',
        'Company:': 'Empresa:',
        'Composite Surfaces': 'Superficies compuestas',
        'Composite Surfaces (slip surface follows a Material Boundary)': 'Superficies compuestas (la superficie de rotura sigue un contorno de material)',
        'Constant u:': 'u constante:',
        'Convergence Options': 'Opciones de convergencia',
        'Convert Boundary': 'Convertir contorno',
        'Convex Surfaces Only': 'Solo superficies convexas',
        'Coordinates of last vertex': 'Coordenadas del último vértice',
        'Correlated with:': 'Correlacionada con:',
        'Correlation coefficient:': 'Coeficiente de correlación:',
        'Create tension crack for reverse curvature': 'Crear grieta de tracción por curvatura inversa',
        'Custom m': 'm personalizado',
        'Default Hu:': 'Hu por defecto:',
        'Defaults': 'Valores por defecto',
        'Define Hydraulic Properties': 'Definir propiedades hidráulicas',
        'Define Tension Crack': 'Definir grieta de tracción',
        'Define Tension Crack hydraulic properties': 'Definir propiedades hidráulicas de la grieta de tracción',
        'Delete Load': 'Eliminar carga',
        'Delete Row': 'Eliminar fila',
        'Delete stage': 'Eliminar etapa',
        'Depth from crack top:': 'Profundidad desde el borde de la grieta:',
        'Discretizations (mesh edges)': 'Discretizaciones (aristas de malla)',
        'Distribution:': 'Distribución:',
        'Divisions along slope:': 'Divisiones a lo largo del talud:',
        'Divisions to use in next iteration:': 'Divisiones para la siguiente iteración:',
        'Drawdown method:': 'Método de desembalse:',
        'Element Numbers': 'Números de elemento',
        'Elevation (Y):': 'Cota (Y):',
        'Elevation (y):': 'Cota (y):',
        'End Angle:': 'Ángulo final:',
        'Enter X,Y:': 'Introducir X,Y:',
        'Expand / Shrink External Boundary': 'Expandir / contraer el contorno externo',
        'External Boundary': 'Contorno externo',
        'Failure Direction:': 'Dirección de rotura:',
        'Fill': 'Relleno',
        'Filter Surfaces': 'Filtrar superficies',
        'Filters (apply to all candidate surfaces)': 'Filtros (se aplican a todas las superficies candidatas)',
        'Flow vectors': 'Vectores de flujo',
        'FoS max:': 'FoS máx:',
        'FoS min:': 'FoS mín:',
        'Function points:': 'Puntos de la función:',
        'General': 'General',
        'Geometry Cleanup': 'Limpieza de geometría',
        'Grayscale': 'Escala de grises',
        'Grid Search Options': 'Opciones de búsqueda en malla',
        'Hatch pattern': 'Patrón de trama',
        'Initial number of surface vertices:': 'Número inicial de vértices de la superficie:',
        'K1 angle (deg from +X):': 'Ángulo de K1 (grados desde +X):',
        'K2 / K1:': 'K2 / K1:',
        'Left Projection Angle': 'Ángulo de proyección izquierdo',
        'Line Width:': 'Grosor de línea:',
        'Load creates excess pore pressure (B-bar method)': 'La carga genera exceso de presión intersticial (método B-bar)',
        'Loads': 'Cargas',
        'Lower Angle (Initial Angle at Toe):': 'Ángulo inferior (ángulo inicial en el pie):',
        'Lower Angle:': 'Ángulo inferior:',
        'Magnitude (end):': 'Magnitud (final):',
        'Magnitude:': 'Magnitud:',
        'Manual:': 'Manual:',
        'Mark FoS = 1.0': 'Marcar FoS = 1.0',
        'Material Boundary': 'Contorno de material',
        'Material:': 'Material:',
        'Materials': 'Materiales',
        'Max Materials:': 'Máx. materiales:',
        'Max Supports:': 'Máx. soportes:',
        'Maximum iterations:': 'Iteraciones máximas:',
        'Mean (deterministic):': 'Media (determinista):',
        'Method:': 'Método:',
        'Methods (enable/disable)': 'Métodos (activar/desactivar)',
        'Miscellaneous': 'Varios',
        'Model:': 'Modelo:',
        'Most influential first — ': 'Más influyente primero — ',
        'Move Down': 'Bajar',
        'Move Up': 'Subir',
        'Multiple Groups': 'Grupos múltiples',
        'New type:': 'Nuevo tipo:',
        'No probabilistic result for this method.': 'Sin resultado probabilístico para este método.',
        'No results to display.': 'No hay resultados que mostrar.',
        'No sensitivity result for this method.': 'Sin resultado de sensibilidad para este método.',
        'No sensitivity result.': 'Sin resultado de sensibilidad.',
        'Node Numbers': 'Números de nodo',
        'Not yet implemented in OGR Slip2D': 'Todavía no implementado en OGR Slip2D',
        'Number of Iterations:': 'Número de iteraciones:',
        'Number of Surfaces:': 'Número de superficies:',
        'Number of annealing generation steps:': 'Número de pasos de generación del recocido:',
        'Number of centres': 'Número de centros',
        'Number of factors of safety compared\\nbefore stopping:': 'Número de factores de seguridad comparados\\nantes de parar:',
        'Number of slices:': 'Número de dovelas:',
        'Number of time steps:': 'Número de pasos de tiempo:',
        'Number of vertices along surface:': 'Número de vértices a lo largo de la superficie:',
        'OK': 'Aceptar',
        'Offset distance:': 'Distancia de desplazamiento:',
        'Only one Drawdown Line is allowed.': 'Solo se permite una línea de desembalse.',
        'Only one Water Table is allowed.': 'Solo se permite un nivel freático.',
        'Optimize Surfaces': 'Optimizar superficies',
        'Orientation:': 'Orientación:',
        'Other settings': 'Otros ajustes',
        'Path Search Options': 'Opciones de búsqueda por caminos',
        'Percent Filled:': 'Porcentaje de relleno:',
        'Permeability': 'Permeabilidad',
        'Permeability Units:': 'Unidades de permeabilidad:',
        'Permeability function': 'Función de permeabilidad',
        'Pick rectangle on canvas (2 clicks)': 'Marcar un rectángulo en el lienzo (2 clics)',
        'Pick…': 'Elegir…',
        'Piezo Line:': 'Línea piezométrica:',
        'Piezometric Line': 'Línea piezométrica',
        'Pivot X (toe):': 'Pivote X (pie):',
        'Pivot X:': 'Pivote X:',
        'Pivot Y (toe):': 'Pivote Y (pie):',
        'Pivot Y:': 'Pivote Y:',
        'Plot distribution…': 'Graficar distribución…',
        'Plot:': 'Gráfico:',
        'Plot…': 'Graficar…',
        'Ponded water': 'Agua embalsada',
        'Pore Fluid Unit Weight:': 'Peso específico del agua:',
        'Pore size index (lambda):': 'Índice de tamaño de poro (lambda):',
        'Project Title:': 'Título del proyecto:',
        'RELATIVE maximum: actual maximum = mean + this value.': 'Máximo RELATIVO: el máximo real es la media más este valor.',
        'RELATIVE minimum: actual minimum = mean - this value.': 'Mínimo RELATIVO: el mínimo real es la media menos este valor.',
        'Radius Increment:': 'Incremento de radio:',
        'Random variables': 'Variables aleatorias',
        'Rapid Drawdown analysis': 'Análisis de desembalse rápido',
        'Relative maximum:': 'Máximo relativo:',
        'Relative minimum:': 'Mínimo relativo:',
        'Remove': 'Quitar',
        'Reset to Auto': 'Restablecer a automático',
        'Right Projection Angle': 'Ángulo de proyección derecho',
        'Rotate Boundary': 'Rotar contorno',
        'Ru coefficient:': 'Coeficiente Ru:',
        'Saturated permeability Ks:': 'Permeabilidad saturada Ks:',
        'Scale Boundary': 'Escalar contorno',
        'Scale display items on zoom': 'Escalar elementos al hacer zoom',
        'Search Method:': 'Método de búsqueda:',
        'Segment Length:': 'Longitud de segmento:',
        'Seismic Load': 'Carga sísmica',
        'Select one or more loads to delete:': 'Seleccione una o más cargas para eliminar:',
        'Selectable entity types': 'Tipos de entidad seleccionables',
        'Selection Filter (Ctrl+F)': 'Filtro de selección (Ctrl+F)',
        'Show Boundary Vertices': 'Mostrar vértices de contorno',
        'Show Grid': 'Mostrar malla',
        'Show Ruler': 'Mostrar regla',
        'Show support face plates and anchorage': 'Mostrar placas y anclajes de los soportes',
        'Simplify Boundary': 'Simplificar contorno',
        'Simulated Annealing Search Options': 'Opciones de búsqueda por recocido simulado',
        'Slip surfaces': 'Superficies de rotura',
        'Slope Search Options': 'Opciones de búsqueda de talud',
        'Soil type:': 'Tipo de suelo:',
        'Stages:': 'Etapas:',
        'Standard deviation:': 'Desviación típica:',
        'Start Angle:': 'Ángulo inicial:',
        'Statistical parameters': 'Parámetros estadísticos',
        'Statistics — OGR Slip2D': 'Estadística — OGR Slip2D',
        'Statistics — Random Variables': 'Estadística — Variables aleatorias',
        'Supports': 'Soportes',
        'Surface Options': 'Opciones de superficie',
        'Surface Type & Algorithm': 'Tipo de superficie y algoritmo',
        'Surface Type:': 'Tipo de superficie:',
        'Surfaces Crossing Point': 'Superficies que pasan por un punto',
        'Sx:': 'Sx:',
        'Sy:': 'Sy:',
        'Target factor of safety:': 'Factor de seguridad objetivo:',
        'Target slope angle:': 'Ángulo de talud objetivo:',
        'Tension Crack': 'Grieta de tracción',
        'The mean is the deterministic value defined in the model.': 'La media es el valor determinista definido en el modelo.',
        'Time Units:': 'Unidades de tiempo:',
        'Tolerance (ε):': 'Tolerancia (ε):',
        'Tolerance for stopping criterion:': 'Tolerancia del criterio de parada:',
        'Tolerance:': 'Tolerancia:',
        'Total population size N for the random slope-tangent search.': 'Tamaño total N de la población para la búsqueda aleatoria de tangentes al talud.',
        'Transient FEA options': 'Opciones de FEA transitorio',
        'Transient Groundwater': 'Agua subterránea transitoria',
        'Transient groundwater analysis': 'Análisis de agua subterránea transitorio',
        'Type:': 'Tipo:',
        'Uniform scaling': 'Escalado uniforme',
        'Units': 'Unidades',
        'Units:': 'Unidades:',
        'Unsaturated permeability model': 'Modelo de permeabilidad no saturada',
        'Upper Angle (Initial Angle at Toe):': 'Ángulo superior (ángulo inicial en el pie):',
        'Upper Angle:': 'Ángulo superior:',
        'Vertices (Nodes)': 'Vértices (nodos)',
        'Water Level:': 'Nivel de agua:',
        'Water Table': 'Nivel freático',
        'Water pressure grid values': 'Valores de la malla de presiones de agua',
        'X max:': 'X máx:',
        'X min:': 'X mín:',
        'X range': 'Rango X',
        'X: 0.000   Y: 0.000': 'X: 0.000   Y: 0.000',
        'Y max:': 'Y máx:',
        'Y min:': 'Y mín:',
        'Y range (above slope)': 'Rango Y (sobre el talud)',
        'a:': 'a:',
        'alpha:': 'alfa:',
        'k_h (horizontal):': 'k_h (horizontal):',
        'k_v (vertical):': 'k_v (vertical):',
        'matplotlib is not installed.': 'matplotlib no está instalado.',
        'n:': 'n:',
        'nx:': 'nx:',
        'ny:': 'ny:',
        'tolerance:': 'tolerancia:',
        'x:': 'x:',
        'y:': 'y:',
        '− Remove': '− Quitar',
        '− Row': '− Fila',

        # --- Menus ----------------------------------------------------
        "File": "Archivo",
        "Edit": "Editar",
        "View": "Vista",
        "Analysis": "Análisis",
        "Boundaries": "Contornos",
        "Loading": "Cargas",
        "Support": "Soporte",
        "Surfaces": "Superficies",
        "Properties": "Propiedades",
        "Tools": "Herramientas",
        "Window": "Ventana",
        "Help": "Ayuda",
        # --- File -----------------------------------------------------
        "New Project": "Nuevo proyecto",
        "Open Project...": "Abrir proyecto...",
        "Close Project": "Cerrar proyecto",
        "Save": "Guardar",
        "Save As...": "Guardar como...",
        "Import DXF...": "Importar DXF...",
        "Export DXF...": "Exportar DXF...",
        "Import Properties...": "Importar propiedades...",
        "Print Preview": "Vista previa de impresión",
        "Print...": "Imprimir...",
        "Page Setup...": "Configurar página...",
        "Print Scale...": "Escala de impresión...",
        "Preferences...": "Preferencias...",
        "Recent Projects": "Proyectos recientes",
        "Exit": "Salir",
        # --- Edit -----------------------------------------------------
        "Undo": "Deshacer",
        "Redo": "Rehacer",
        "Copy Image": "Copiar imagen",
        # --- View -----------------------------------------------------
        "Zoom All": "Zoom total",
        "Zoom In": "Aumentar zoom",
        "Zoom Out": "Reducir zoom",
        "Pan": "Desplazar",
        "Zoom Window": "Zoom ventana",
        "Ruler": "Regla",
        "Grid": "Rejilla",
        "Snap": "Snap",
        "Display Options...": "Opciones de visualización...",
        "Grayscale": "Escala de grises",
        # --- Analysis -------------------------------------------------
        "Project Settings...": "Ajustes de proyecto...",
        "Compute": "Calcular",
        "Interpret": "Interpretar",
        "Info Viewer": "Visor de información",
        "Slope Stability Mode": "Modo de estabilidad de taludes",
        "Steady State Groundwater Mode": "Modo de flujo en régimen permanente",
        "Transient Groundwater Mode": "Modo de flujo transitorio",
        # --- Boundaries -----------------------------------------------
        "Add External Boundary": "Añadir contorno externo",
        "Add Material Boundary": "Añadir contorno de material",
        "Add Water Table": "Añadir nivel freático",
        "Add Piezometric Line": "Añadir línea piezométrica",
        "Add Tension Crack": "Añadir grieta de tracción",
        "Simplify Boundary...": "Simplificar contorno...",
        "Geometry Cleanup...": "Limpiar geometría...",
        "Delete Boundary": "Eliminar contorno",
        "Move Vertex": "Mover vértice",
        "Insert Vertex": "Insertar vértice",
        "Delete Vertex": "Eliminar vértice",
        # --- Loading --------------------------------------------------
        "Add Distributed Load...": "Añadir carga distribuida...",
        "Add Line Load...": "Añadir carga lineal...",
        "Seismic Load...": "Carga sísmica...",
        "Delete Load": "Eliminar carga",
        # --- Support --------------------------------------------------
        "Add Support": "Añadir soporte",
        "Add Support Pattern...": "Añadir patrón de soportes...",
        "Delete Support": "Eliminar soporte",
        # --- Surfaces -------------------------------------------------
        "Surface Options...": "Opciones de superficie...",
        "Auto Grid": "Rejilla automática",
        "Add Grid": "Añadir rejilla",
        "Add Surface (three points)": "Añadir superficie (tres puntos)",
        "Define Limits...": "Definir límites...",
        # --- Properties -----------------------------------------------
        "Define Materials...": "Definir materiales...",
        "Define Support...": "Definir soporte...",
        "Assign Materials": "Asignar materiales",
        # --- Water surfaces (v0.1.62) ---------------------------------
        "Assign Water Surface...": "Asignar superficie de agua...",
        "Assign Water Surface": "Asignar superficie de agua",
        "Water Surface:": "Superficie de agua:",
        "Water Table": "Nivel freático",
        "Piezometric Line": "Línea piezométrica",
        "(first of this type)": "(la primera de este tipo)",
        "Apply to materials": "Aplicar a los materiales",
        "This project has no materials yet.":
            "Este proyecto todavía no tiene materiales.",
        "Draw a water table or a piezometric line first.":
            "Dibuja antes un nivel freático o una línea piezométrica.",
        "Water surface this material takes its pore pressure from. "
        "It must span every abscissa the material occupies.":
            "Superficie de agua de la que este material toma su presión "
            "intersticial. Debe estar definida en toda la abscisa que "
            "ocupa el material.",
        "Hu coefficient": "Coeficiente Hu",
        "u = γw · Hu · h, with h the vertical distance up to the "
        "water surface. Unchecked, the project default applies.":
            "u = γw · Hu · h, siendo h la distancia vertical hasta la "
            "superficie de agua. Sin marcar, se usa el valor por defecto "
            "del proyecto.",
        "Auto Hu (cos²α from the water-surface slope)":
            "Hu automático (cos²α de la pendiente de la superficie)",
        "Assumes the equipotential through the slice base is straight, "
        "which is exact only for an infinite slope.":
            "Supone que la equipotencial que pasa por la base de la dovela "
            "es recta, lo que solo es exacto en talud infinito.",
        "Ordinary/Fellenius: %d of %d slices had a negative "
        "effective normal force; its FoS is underestimated.":
            "Ordinary/Fellenius: %d de %d dovelas tuvieron fuerza normal "
            "efectiva negativa; su FS está subestimado.",
        # --- Multi-stage rapid drawdown (v0.1.68) ---------------------
        "Effective Stress using B-bar": "Tensiones efectivas con B-barra",
        "Duncan, Wright, Wong 3 Stage (1990)":
            "Duncan, Wright, Wong 3 etapas (1990)",
        "Army Corp. Eng. 2 Stage (1970)":
            "Cuerpo de Ingenieros 2 etapas (1970)",
        "Lowe and Karafiath (1960)": "Lowe y Karafiath (1960)",
        "Rapid Drawdown": "Descenso rápido",
        "Undrained envelope:": "Envolvente no drenada:",
        "Total Stress R Envelope": "Envolvente R en tensiones totales",
        "Kc = 1 Envelope": "Envolvente Kc = 1",
        "(none)": "(ninguna)",
        "Cr:": "Cr:",
        "Angle:": "Ángulo:",
        "d:": "d:",
        "Psi:": "Psi:",
        "All four procedures require the groundwater method to be "
        "Water Surfaces and at least one material marked as "
        "undrained. The three multi-stage ones also need an R or "
        "Kc=1 envelope on it; B-bar needs its B-bar coefficient.":
            "Los cuatro procedimientos exigen que el método de agua sea "
            "superficies de agua y que al menos un material esté marcado "
            "como no drenado. Los tres multietapa necesitan además una "
            "envolvente R o Kc=1 en él; B-barra, su coeficiente B-barra.",
        "Undrained envelope from isotropically consolidated undrained "
        "tests. Needed by the multi-stage drawdown procedures.":
            "Envolvente no drenada de ensayos consolidados isótropos no "
            "drenados. La necesitan los procedimientos multietapa.",
        "Excess pore pressure from loading, on materials marked as "
        "undrained. This is a separate analysis from Rapid Drawdown, "
        "not a prerequisite for it: the two are mutually exclusive.":
            "Exceso de presión intersticial por carga, en materiales "
            "marcados como no drenados. Es un análisis distinto del "
            "descenso rápido, no un requisito: son excluyentes.",
        "Enables the Drawdown Line tool and computes the factor of "
        "safety after the drawdown. The water table is the INITIAL "
        "level and the drawdown line the final, lower one.":
            "Habilita la herramienta de línea de desembalse y calcula el "
            "factor de seguridad tras el descenso. El nivel freático es el "
            "nivel INICIAL y la línea de desembalse el final, más bajo.",
        # --- Excess pore pressure, B-bar method (v0.1.75) -------------
        "Excess Pore Pressure": "Exceso de presión intersticial",
        "Material weight creates excess pore pressure":
            "El peso del material genera exceso de presión intersticial",
        "Skempton's B̄: Δu = B̄ · Δσv. Use 0 for a free-draining "
        "material, which then develops no excess however much load "
        "arrives.":
            "B̄ de Skempton: Δu = B̄ · Δσv. Usa 0 para un material "
            "drenante libre, que entonces no desarrolla exceso por mucha "
            "carga que le llegue.",
        "This material's weight loads the materials BENEATH it. It "
        "is a separate question from whether this material develops "
        "excess itself, which is its own B-bar: an embankment over a "
        "clay foundation usually has this on and B-bar = 0.":
            "El peso de este material carga a los materiales que tiene "
            "DEBAJO. Es una pregunta distinta de si este material "
            "desarrolla exceso él mismo, que es su propio B-barra: un "
            "terraplén sobre cimiento arcilloso suele llevar esto "
            "activado y B-barra = 0.",
        # --- Project Settings wiring (v0.1.74) -------------------------
        "Check m-alpha < 0.2": "Comprobar m-alfa < 0.2",
        "Rejects surfaces whose base normal denominator falls below "
        "0.2 (Whitman and Bailey, 1967).":
            "Rechaza las superficies cuyo denominador de la normal de "
            "base baja de 0.2 (Whitman y Bailey, 1967).",
        "The m-alpha check is ON by default, as in the reference, "
        "which screens surfaces with it and reports them as error "
        "-112. Surfaces it rejects keep their factor of safety and "
        "stay in the results; they are only barred from being the "
        "critical surface. Switch it off to see them compete.":
            "La comprobación de m-alfa está ACTIVADA por defecto, como en "
            "la referencia, que filtra superficies con ella y las informa "
            "como error -112. Las superficies que rechaza conservan su "
            "factor de seguridad y siguen en los resultados; solo se les "
            "impide ser la superficie crítica. Desactívala para verlas "
            "competir.",
        "Percentage of slices:": "Porcentaje de dovelas:",
        "Percentage of slices, counted from the toe, over which the "
        "tensile check applies.":
            "Porcentaje de dovelas, contado desde el pie, sobre el que se "
            "aplica la comprobación de tracción.",
        "Aitken extrapolation of the fixed-point iteration. It "
        "converges to the same root: on the reference-validated "
        "circle both agree to 1e-11, and it needs 7 passes instead "
        "of 19.":
            "Extrapolación de Aitken de la iteración de punto fijo. "
            "Converge a la misma raíz: en el círculo validado contra la "
            "referencia ambos coinciden hasta 1e-11, y necesita 7 pasadas "
            "en lugar de 19.",
        "First trial value of the factor of safety. A starting "
        "point, not a floor.":
            "Primer valor de tanteo del factor de seguridad. Un punto de "
            "partida, no un mínimo.",
        "Search range for the interslice force scaling factor used by "
        "Spencer and GLE / Morgenstern-Price. It clips a calibrated "
        "grid rather than replacing it; narrowing it below 1.5 can "
        "exclude the solution, as the reference circle of the "
        "validation case needs lambda = 1.49.":
            "Rango de búsqueda del factor de escala de las fuerzas entre "
            "dovelas que usan Spencer y GLE / Morgenstern-Price. Recorta "
            "una rejilla calibrada en lugar de sustituirla; estrecharlo "
            "por debajo de 1.5 puede excluir la solución, ya que el "
            "círculo de referencia del caso de validación necesita "
            "lambda = 1.49.",
        "Interslice force function:": "Función de fuerzas entre dovelas:",
        "Half Sine": "Medio seno",
        "Constant": "Constante",
        "Trapezoidal": "Trapezoidal",
        "Clipped Sine": "Seno recortado",
        "Shape of the interslice force function used by GLE / "
        "Morgenstern-Price. Constant makes GLE equivalent to "
        "Spencer. x runs from 0 at the LEFT end of the surface to 1 "
        "at the right, whatever the failure direction.":
            "Forma de la función de fuerzas entre dovelas que usa GLE / "
            "Morgenstern-Price. Constante hace GLE equivalente a Spencer. "
            "x va de 0 en el extremo IZQUIERDO de la superficie a 1 en el "
            "derecho, sea cual sea la dirección de rotura.",
        "None": "Ninguna",
        "Transient groundwater": "Filtración transitoria",
        "Staged transient seepage. Its solver options are on the "
        "Transient page, which this switch enables.":
            "Filtración transitoria por etapas. Sus opciones de solver "
            "están en la página Transitorio, que este selector habilita.",
        "Transient groundwater:": "Filtración transitoria:",
        "On": "Activada",
        "Off — switch it on under Groundwater → Advanced":
            "Desactivada — actívala en Agua subterránea → Avanzado",
        "Share one Latin Hypercube stratification across variables":
            "Compartir una estratificación de hipercubo latino entre "
            "variables",
        "Sample i then sits in the same stratum of every variable, so "
        "they move together. It answers a different question from the "
        "independent case and usually widens the spread. No effect on "
        "Monte Carlo, which has no strata to share.":
            "La muestra i queda entonces en el mismo estrato de todas las "
            "variables, así que se mueven juntas. Responde a una pregunta "
            "distinta del caso independiente y suele ampliar la "
            "dispersión. No afecta a Monte Carlo, que no tiene estratos "
            "que compartir.",
        "Applies to the probabilistic and sensitivity analyses and "
        "to the random surface searches (Slope, Block, Path and "
        "Simulated Annealing). Grid and Auto Refine enumerate their "
        "surfaces, so nothing there is drawn at random.":
            "Se aplica a los análisis probabilístico y de sensibilidad y "
            "a las búsquedas aleatorias de superficies (talud, bloque, "
            "trayectoria y recocido simulado). Rejilla y refinado "
            "automático enumeran sus superficies, así que ahí no se "
            "sortea nada.",
        # --- Failure direction, with a picture of it (v0.1.73) ---------
        "Right to Left": "De derecha a izquierda",
        "Left to Right": "De izquierda a derecha",
        "The sliding mass moves towards decreasing x: the crest is "
        "on the right and the toe on the left.":
            "La masa deslizante se mueve hacia x decreciente: la coronación "
            "queda a la derecha y el pie a la izquierda.",
        "The sliding mass moves towards increasing x: the crest is "
        "on the left and the toe on the right.":
            "La masa deslizante se mueve hacia x creciente: la coronación "
            "queda a la izquierda y el pie a la derecha.",
        # --- Water parameters, where the reference puts them (v0.1.72) -
        "Water Parameters": "Parámetros de agua",
        "Use the water pressure grid": "Usar la rejilla de presiones",
        "With the grid off, this material takes its pore pressure "
        "from its own water parameters instead of the grid.":
            "Con la rejilla desactivada, este material toma su presión "
            "intersticial de sus propios parámetros de agua en lugar de "
            "la rejilla.",
        "Define Strength...": "Definir resistencia...",
        "Define Strength": "Definir resistencia",
        "Undrained envelope from isotropically consolidated undrained "
        "tests. Either form is accepted: the conversion between them "
        "is exact, and each procedure is given the one it needs.":
            "Envolvente no drenada de ensayos consolidados isótropos no "
            "drenados. Se admite cualquiera de las dos formas: la "
            "conversión entre ellas es exacta, y a cada procedimiento se "
            "le da la que necesita.",
        "R: Cr = %.4g, φR = %.4g°": "R: Cr = %.4g, φR = %.4g°",
        "Kc = 1: d = %.4g, ψ = %.4g°": "Kc = 1: d = %.4g, ψ = %.4g°",
        # --- Rapid drawdown parameters (v0.1.62) ----------------------
        "Rapid Drawdown Parameters": "Parámetros de descenso rápido",
        "Undrained Behaviour": "Comportamiento no drenado",
        "B-bar:": "B-barra:",
        "Skempton's B̄: Δu = B̄ · Δσv. Only a material that behaves "
        "undrained retains excess pore pressure after drawdown.":
            "B̄ de Skempton: Δu = B̄ · Δσv. Solo un material de "
            "comportamiento no drenado retiene exceso de presión "
            "intersticial tras el desembalse.",
        "Enable Rapid Drawdown analysis in Project Settings "
        "→ Groundwater → Advanced first.":
            "Activa antes el análisis de descenso rápido en Ajustes del "
            "proyecto → Agua subterránea → Avanzado.",
        # --- Drawdown level sweep (v0.1.70) ---------------------------
        "Drawdown Level Sweep...": "Barrido de niveles de desembalse...",
        "Drawdown Level Sweep": "Barrido de niveles de desembalse",
        "Number of levels:": "Número de niveles:",
        "Include total drawdown": "Incluir desembalse total",
        "Drawdown level (y)": "Nivel de desembalse (y)",
        "Factor of safety vs drawdown level":
            "Factor de seguridad frente al nivel de desembalse",
        "Critical drawdown level": "Nivel de desembalse crítico",
        "total drawdown": "desembalse total",
        "the total drawdown alone would overstate it by":
            "analizar solo el desembalse total lo sobrestimaría en un",
        "No level produced a valid factor of safety.":
            "Ningún nivel produjo un factor de seguridad válido.",
        "Reservoir levels between the initial water table and the "
        "lowest ground in the model. Each one is a full search, so "
        "this is the cost of the run.":
            "Niveles del embalse entre el nivel freático inicial y la cota "
            "de terreno más baja del modelo. Cada uno es una búsqueda "
            "completa, así que es lo que cuesta la corrida.",
        "Search at a range of reservoir levels. The total "
        "drawdown is not always the critical one.":
            "Busca en un rango de niveles del embalse. El desembalse total "
            "no siempre es el crítico.",
        "Enable Rapid Drawdown analysis in Project Settings "
        "> Groundwater > Advanced first.":
            "Activa antes el análisis de descenso rápido en Ajustes del "
            "proyecto > Agua subterránea > Avanzado.",
        # --- Tools ----------------------------------------------------
        "Add Text": "Añadir texto",
        "Measure": "Medir",
        "Dimension Length": "Acotar longitud",
        "Dimension Angle": "Acotar ángulo",
        "Material Properties Table": "Tabla de propiedades de materiales",
        # --- Window ---------------------------------------------------
        "New Window": "Nueva ventana",
        "Cascade": "Cascada",
        "Tile Horizontally": "Mosaico horizontal",
        "Tile Vertically": "Mosaico vertical",
        # --- Help -----------------------------------------------------
        "Help Topics": "Temas de ayuda",
        "About OGR Slip2D": "Acerca de OGR Slip2D",
        "Check for Updates": "Buscar actualizaciones",
        # --- Common UI ------------------------------------------------
        "OK": "Aceptar",
        "Cancel": "Cancelar",
        "Apply": "Aplicar",
        "Defaults...": "Valores por defecto...",
        "Name": "Nombre",
        "Color": "Color",
        "Type": "Tipo",
        "Cohesion": "Cohesión",
        "Friction Angle": "Ángulo de rozamiento",
        "Unit Weight": "Peso específico",
        "Saturated Unit Weight": "Peso específico saturado",
        # v0.1.60 — casilla de peso específico saturado
        "Different unit weights above and below the water table. "
        "Requires a water table in the model.":
            "Pesos específicos distintos por encima y por debajo del nivel "
            "freático. Requiere un nivel freático en el modelo.",
        "Saturated bulk unit weight, used below the water table. "
        "It is not the submerged (buoyant) unit weight, so it "
        "should be greater than the unit weight above.":
            "Peso específico aparente saturado, aplicado por debajo del "
            "nivel freático. No es el peso específico sumergido, así que "
            "debe ser mayor que el peso específico por encima.",
        "The saturated unit weight should be greater than the "
        "unit weight above the water table.":
            "El peso específico saturado debería ser mayor que el peso "
            "específico por encima del nivel freático.",
        "Strength Type": "Tipo de resistencia",
        "Pore Pressure": "Presión intersticial",
        "Water Surface": "Superficie de agua",
        "Ready": "Listo",
        "Computing...": "Calculando...",
        "Critical FoS": "FS crítico",
        "Language": "Idioma",
        "Theme": "Tema",
        "Light": "Claro",
        "Dark": "Oscuro",
        # Status bar
        "Coordinates": "Coordenadas",
        "SNAP": "SNAP",
        "GRID": "REJILLA",
        "ORTHO": "ORTO",
        "OSNAP": "OSNAP",
    },
}

_LANG = "en"
_LISTENERS: list[Callable[[str], None]] = []


def set_language(code: str) -> None:
    """Switch the active language. Emits a notification to listeners."""
    global _LANG
    if code not in _DICTS:
        raise KeyError(f"Unknown language '{code}'. Available: {list(_DICTS)}")
    _LANG = code
    for cb in list(_LISTENERS):
        try:
            cb(code)
        except Exception:  # noqa: BLE001
            pass


def current_language() -> str:
    return _LANG


def available_languages() -> list[str]:
    return list(_DICTS.keys())


def on_language_changed(cb: Callable[[str], None]) -> None:
    _LISTENERS.append(cb)


def tr(key: str) -> str:
    """Translate ``key`` into the active language (falls back to the key)."""
    return _DICTS.get(_LANG, {}).get(key, key)


def add_translations(lang: str, mapping: dict[str, str]) -> None:
    """Register additional translations at runtime (for plugins)."""
    _DICTS.setdefault(lang, {}).update(mapping)
