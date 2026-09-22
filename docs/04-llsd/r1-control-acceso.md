# LLSD R1 — Control de acceso a la red por rol

> Diseño de bajo nivel: las estructuras de datos, el flujo concreto y los
> archivos que implementan el HLD (`docs/03-hld/r1-control-acceso.md`) y la
> decisión AD-02 del documento de arquitectura del Lab 3. Se escribe junto
> con el código, no después — si el código cambia, este documento cambia en
> el mismo PR.

## Archivos

| Archivo | Responsabilidad |
|---|---|
| `src/common/pipeline.py` | Constantes del contrato de tablas (tablas, rangos de prioridad, codificación de `metadata`) — fuente única, la importan todos los módulos |
| `src/common/eventbus.py` | Bus de eventos en memoria (M06), patrón message-queueing |
| `src/common/l2_forwarding.py` | Tabla 4 (reenvío L2 real) + reglas de paso temporales en las tablas 0, 1 y 3, mientras R2 y R3 no existan |
| `src/controller/r1_auth/roles.py` | `TablaDeRoles`: lógica pura de rol por MAC, sin red — se prueba con pytest normal |
| `src/controller/r1_auth/app.py` | App de os-ken: tabla 2 del pipeline, identidad y escritura de `metadata` |
| `tests/unit/test_r1_roles.py`, `test_pipeline_metadata.py` | Pruebas unitarias, corren en CI sin switch |

## Estructuras de datos

```python
TablaDeRoles._roles: dict[str, int]        # MAC -> rol (0-4)
ControlDeAccesoR1.datapaths: dict[int, Datapath]   # dpid -> datapath, para poder revocar bajo demanda
ControlDeAccesoR1.sesiones: dict[str, dict]        # MAC -> {dpid, in_port, rol, estado}
```

`TablaDeRoles` arranca vacía. Hoy se puebla solo si se le pasan `roles_iniciales` al construirla (útil para pruebas); la Northbound API que la llenaría en producción (`POST /r1/...`) queda deliberadamente fuera de este primer incremento — ver "Qué queda fuera" más abajo.

## Flujo concreto (primer paquete de un host)

1. El host manda su primer paquete. Cruza las tablas 0 y 1 por las reglas de paso de `l2_forwarding.py` (R3 aún no existe) y llega a la tabla 2 sin coincidir con nada: table-miss, `Packet-In` a R1.
2. `_packet_in` filtra por `msg.table_id == TABLA_IDENTIDAD` (2), para no reaccionar a misses de otras tablas.
3. `TablaDeRoles.resolver(mac)` devuelve `(rol, es_desconocida)`. Si es desconocida, rol mínimo (alumno) y se loguea para auditoría — tal como pide el HLD §3.
4. Se guarda la sesión (`dpid`, `in_port`, `rol`, `estado=AUTENTICADO`) en memoria.
5. `_instalar_regla_identidad`: instala en la tabla 2, prioridad `PRIO_R1_MIN` (20000), match `(in_port, eth_src)` exacto, con `write_metadata(codificar_metadata(rol, estado), 0xFF)` + `goto_table(TABLA_POLITICA)`.
6. `_reenviar_paquete_original`: `PacketOut` con acción `OFPP_TABLE`, que reingresa el paquete por la tabla 0. Con las reglas de paso ya instaladas, vuelve a llegar a la tabla 2 — pero esta vez coincide con la regla recién creada, así que ya no genera un `Packet-In` nuevo.
7. Se publica `host_autenticado` en el bus, con `dpid`, `in_port`, `mac`, `rol`.

Los paquetes siguientes del mismo host ya no tocan al controlador: la regla de la tabla 2 los resuelve a velocidad de línea. Esto es lo que sostiene la escalabilidad medida en la Fase 4 (§8-9 del HLD).

## Revocación reactiva

`ControlDeAccesoR1` se suscribe a `ataque_detectado` en `__init__`. Cuando R3 lo emita: busca la sesión por MAC, si existe reinstala la misma regla de tabla 2 con `estado=REVOCADO` (mismo match → Word sobreescribe la entrada existente, no duplica), y publica `sesion_revocada`. R2 consumirá ese evento para propagar el bloqueo — ver contrato de eventos.

**Nota de diseño:** revocar no borra la regla ni manda al host de vuelta al table-miss. Deja la regla activa pero con `estado=REVOCADO` en `metadata`, para que R2 (que lee el estado, no solo el rol) pueda decidir denegar incluso recursos antes permitidos, sin que el host tenga que volver a generar un `Packet-In` para eso.

## Validado contra el VNRT (2026-09-22)

Corrida real, no solo unitaria: `python tools/osken_run.py src.controller.r1_auth.app src.common.l2_forwarding` en el nodo `controller`, conectado a los tres switches reales (`sw1`, `sw2`, `sw3`).

- `ping -c 4` de `h1` (10.0.0.1) a `h2` (10.0.0.2): **4/4 recibidos, 0% de pérdida**, de punta a punta a través del pipeline completo (tablas 0→1→2→3→4).
- Ambas MAC (`fa:16:3e:9f:b2:02`=h1, `fa:16:3e:bb:e9:aa`=h2) llegaron a R1 sin estar registradas, degradaron a rol alumno tal como especifica el HLD §3, y quedaron logueadas para auditoría.
- Regla instalada en `sw2`, tabla 2: `priority=20000,in_port=2,dl_src=fa:16:3e:9f:b2:02 actions=write_metadata:0x11/0xff,goto_table:3` — `0x11` es exactamente `codificar_metadata(ROL_ALUMNO, ESTADO_AUTENTICADO)`, confirmando que la codificación de bits del contrato se aplica igual en código que en el switch real.
- El mismo host se identificó de forma independiente en `sw1` y `sw3` también (el tráfico ARP de resolución cruzó esos switches) — comportamiento esperado: cada switch aplica su propia regla local, no hay un punto central de decisión por paquete.

De paso se encontró y se limpió un residuo: el controlador de la Fase 5 (`bench_ataques.py`) había quedado corriendo desde el 17 de septiembre sin que nadie lo detuviera, ocupando el puerto 6653. Se detuvo antes de esta prueba.

## Qué queda fuera de este incremento (deuda declarada, no oculta)

- **Northbound API REST** (`GET /r1/sesiones`, `/r1/metricas`, `/r1/roles`, `POST /r1/revocar`, del HLD §10): no implementada. `TablaDeRoles` hoy solo se puebla programáticamente. Es el siguiente incremento natural, y necesita decidir el framework HTTP (no es una decisión de arquitectura nueva, es de implementación — queda para cuando se retome).
- **Persistencia de `sesiones`**: vive en memoria del proceso. Si el controlador se reinicia, se pierde el estado (consistente con "controlador único, sin cluster" del modelo de control del Ex1 — ver §9 del documento de arquitectura del Lab 3).
- **Revocación reactiva** (`ataque_detectado` → sesión revocada): implementada y con lógica probada por unit test indirectamente (la codificación de metadata), pero **no probada end-to-end contra el VNRT** porque requiere que R3 exista para emitir el evento real. Queda pendiente de una prueba de integración cuando R3 esté listo.
