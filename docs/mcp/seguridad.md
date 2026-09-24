# Seguridad del servidor MCP

## `python_exec` es ejecución de código, por diseño

El servidor publica siempre la herramienta `python_exec`, que ejecuta Python
arbitrario en el proceso del servidor con los permisos del usuario que lo
arrancó. Es una decisión del propietario (2026-09-24), la misma que toman los
servidores MCP de Blender y de QGIS: cubre todo lo que aún no tiene
herramienta propia.

La consecuencia es sencilla: **quien pueda hablar con el servidor puede
ejecutar código en tu máquina.** Todo lo demás se sigue de ahí.

## stdio

Con stdio (Claude, LM Studio, OpenAI Agents SDK) el servidor es un proceso
hijo del cliente y no abre ningún puerto. El riesgo que queda es la
**inyección de instrucciones**: un texto que el modelo lea —un archivo, una
web— puede pedirle que ejecute algo. Los clientes que piden confirmación antes
de cada herramienta (Claude Desktop, Claude Code) son la defensa; no la
desactives para `python_exec`.

## HTTP

- **Token siempre, también en 127.0.0.1.** «Sólo local» no es una frontera:
  cualquier página que visites puede hacer que tu navegador envíe peticiones
  a `localhost`. El token se compara en tiempo constante.
- **Host y Origin comprobados.** La protección contra *DNS rebinding* del SDK
  está activada: un `Host` que no es el del servidor recibe 421, y un
  `Origin` ajeno 403, incluso con token. `--allow-origin` añade orígenes.
- **Sin token no hay red.** Con un `--host` que no sea de *loopback*, el
  servidor exige un token explícito (`--token-file` u `OGR_MCP_TOKEN`) y se
  niega a arrancar sin él (código de salida 2). `--no-auth` sólo se acepta en
  *loopback*.
- Prefiere `--token-file` o la variable `OGR_MCP_TOKEN` a `--token`: un
  argumento de la línea de órdenes lo ven los demás usuarios de la máquina.

## Archivos

Las rutas relativas se resuelven contra `--workdir`. Guardar nunca
sobrescribe un archivo existente sin `overwrite=true`, salvo el propio archivo
del modelo, que es lo que significa guardar.

## Red y telemetría

El servidor no hace ninguna llamada de red por su cuenta. La dependencia
`opentelemetry-api` que trae el SDK es sólo la API: sin un SDK de telemetría
configurado, no exporta nada.
