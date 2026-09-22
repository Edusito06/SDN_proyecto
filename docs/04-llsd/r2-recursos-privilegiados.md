# LLSD R2 — Restricción de acceso a recursos privilegiados

> Diseño de bajo nivel: implementa el HLD (`docs/03-hld/r2-recursos-privilegiados.md`)
> y la decisión AD-03. Se escribe junto con el código, en el mismo PR.

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `src/controller/r2_policy/slice.py` | Modelo declarativo (`Recurso`, `Slice`) y `compilar()`: slice → lista de reglas abstractas. Lógica pura, sin OpenFlow — se prueba con pytest normal |
| `src/controller/r2_policy/app.py` | App de os-ken: tabla 3 del pipeline, traduce las reglas compiladas a `OFPFlowMod` reales, maneja denegaciones y la propagación de bloqueos |
| `tests/unit/test_r2_slice.py` | 11 pruebas unitarias del modelo de slice |

## Decisión de diseño: R2 es proactivo, no reactivo como R1

A diferencia de R1 (que instala una regla por host, disparada por su primer paquete), R2 **compila todo el slice de una vez al conectar el switch**. No necesita esperar a ver tráfico: en cuanto sabe qué recursos existen y qué roles los pueden usar, ya sabe todas las reglas que va a instalar. Esto es consistente con el HLD §4 ("Traducción a reglas OpenFlow"): la tabla de 7 reglas del ejemplo es estática, no se arma paquete por paquete.

## El slice de esta corrida

Hardcodeado en `SLICE_POR_DEFECTO` (la Northbound API que lo cargaría en producción queda para después, igual que en R1), usando los recursos reales que ya están marcados como críticos en el mapa del VNRT (`docs/diagramas/topologia-vnrt.md`):

| Recurso | Destino | Protocolo | Roles permitidos |
|---|---|---|---|
| `servidor-notas` | `10.0.0.3` (h3) | ICMP | docente, superusuario |
| `repo-examenes` | `10.0.0.4` (h4) | ICMP | superusuario |

Se usa ICMP en vez de TCP/443 (como el ejemplo del HLD) porque h3/h4 en el VNRT no corren ningún servicio en ese puerto — ICMP (`ping`) es lo que de verdad se puede probar de punta a punta contra el entorno real, sin inventar un servidor. El mecanismo (`slice.py`, `app.py`) es agnóstico al protocolo: agregar un recurso TCP/UDP real es una línea en `SLICE_POR_DEFECTO`, no un cambio de diseño.

## Cómo se traduce una regla del slice a OpenFlow

**Permiso** (ej. docente → servidor-notas): `match(metadata=codificar_metadata(ROL_DOCENTE, ESTADO_AUTENTICADO)/0xFF, eth_type=IP, ip_proto=1, ipv4_dst=10.0.0.3)`, prioridad 39000, `goto_table(REENVIO)`.

**Por qué el match incluye el estado, no solo el rol:** si matcheara solo el rol, una sesión revocada por R3 (que R1 marca con `estado=REVOCADO` en la misma `metadata`, sin tocar el rol) seguiría coincidiendo con el permiso. Al exigir `estado=AUTENTICADO` exacto en el match, la revocación de R1 invalida el permiso de R2 automáticamente, sin que R2 tenga que suscribirse a `sesion_revocada` ni hacer nada extra — es una consecuencia directa de cómo R1 escribe `metadata`, no lógica adicional de R2.

**Denegación** (cualquiera que no matcheó ningún permiso, hacia ese recurso): `match(eth_type=IP, ip_proto=1, ipv4_dst=10.0.0.3)`, sin filtro de rol, prioridad 41000, acción = enviar al controlador. Es la que registra el intento (`acceso_denegado` al bus) la primera vez.

**Bloqueo temporal por host** (`PRIO_DENIEGA_HOST_TEMPORAL` = 45000, `idle_timeout=10`): se instala reactivamente, solo cuando la denegación genérica ya disparó un `Packet-In`. Es más específica (agrega `in_port` + `eth_src`) y de mayor prioridad, así que mientras dura, el mismo host repitiendo el mismo intento se descarta en el switch sin volver a tocar al controlador — HLD §4, "Ciclo de vida de una denegación". Al expirar, si el host insiste, se genera un `Packet-In` nuevo: esa repetición es justo la señal que R3 usará como indicio de reconocimiento.

**Bloqueo por ataque confirmado** (`PRIO_DENIEGA_ATAQUE` = 48000, sin timeout): al consumir `ataque_detectado`, se instala en **todos** los switches conocidos (`self.datapaths`), no solo el que vio el ataque — HLD §5: "R2 reacciona propagando el bloqueo al resto de switches". Se queda hasta intervención manual, coherente con el nivel 3 de la escalera de R3.

## Bug encontrado en vivo: la denegación genérica le ganaba a un permiso válido

Primera versión: la denegación genérica por recurso vivía en 41000 (dentro del rango "denegaciones explícitas" 40000-49999 del contrato, tal como sugiere literalmente el ejemplo del HLD §4). Al probar contra el VNRT real, un host registrado como **superusuario** seguía sin poder hacer ping a `h3`/`h4` — el permiso (39000) nunca ganaba.

**Causa:** en OpenFlow gana la prioridad numérica más alta, sin importar qué tan específico sea el match de cada regla. La denegación genérica (`match: icmp, dst=10.0.0.3`, sin filtro de rol) y el permiso (`match: icmp, dst=10.0.0.3, metadata=rol exacto`) pueden coincidir con el mismo paquete; como 41000 > 39000, la denegación ganaba siempre, incluso para un rol autorizado.

**Fix:** la denegación genérica por recurso baja a 35000 — todavía dentro del espacio que R2 controla (30000-49999), pero por debajo del permiso (39000) y por encima del defecto (30000), para que la cadena de prioridad quede: *permiso > denegación genérica > defecto > table-miss*. El rango 40000-49999 queda reservado para los bloqueos que sí deben ganarle a un permiso válido (host puntual tras un intento denegado, o propagado por `ataque_detectado`) — esos dos siguen donde estaban, y **su comportamiento no cambió** (ver pruebas más abajo).

Se agregó `test_permiso_tiene_mayor_prioridad_que_la_denegacion_generica` a `test_r2_slice.py` como prueba de regresión — este bug debió atraparse ahí antes de llegar al VNRT, y ahora sí se atraparía.

## Validado contra el VNRT (2026-09-22)

- **Denegación:** `h1` sin rol registrado (alumno por defecto) → ping a `h3` (10.0.0.3): 100% de pérdida. Log confirma `acceso denegado... recurso=servidor-notas` y el evento `acceso_denegado` publicado. La regla temporal (`priority=45000, idle_timeout=10, in_port + eth_src + ipv4_dst, actions=drop`) se vio activa en vivo durante la ventana de 10s, y expiró sola después — confirmado con `dump-flows` a mitad de la prueba.
- **Permiso (tras corregir el bug de prioridades):** `h1` registrado como superusuario (vía `roles_iniciales` temporal, solo para la prueba, revertido después) → ping a `h3` **y** a `h4`: 3/3 recibidos, 0% de pérdida, en ambos.
- **Regresión:** repetido el caso de alumno denegado después del fix — sigue denegado, 100% de pérdida. El fix no rompió el camino de denegación.
- Nota metodológica: reiniciar el controlador **no** limpia los flujos ya instalados en los switches (son independientes). Para volver a probar con un rol distinto para el mismo host hay que limpiar las tablas (`ovs-ofctl del-flows`) o esperar a que las reglas expiren; si no, el switch sigue aplicando la decisión vieja sin volver a preguntarle al controlador.

## Qué queda fuera de este incremento

- **Northbound API REST** para cargar el slice dinámicamente — igual que en R1, es el siguiente incremento natural.
- **Recursos TCP/UDP reales**: el modelo los soporta (`slice.py` es agnóstico al protocolo), pero esta corrida solo prueba ICMP porque es lo que hay disponible en el VNRT para probar sin montar un servicio nuevo.
- **Liberación del bloqueo por ataque**: se instala pero no hay todavía un mecanismo (Northbound API) para retirarlo — coherente con que el HLD dice "hasta intervención del administrador", pero esa intervención no tiene endpoint aún.
