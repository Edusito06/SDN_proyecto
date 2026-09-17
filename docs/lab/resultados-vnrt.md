# Resultados del reconocimiento del VNRT

Plantilla que se llena ejecutando `00-reconocimiento-vnrt.md`. Cada dato lleva el
comando que lo produjo. Si algo no se pudo medir, se escribe el motivo, nunca un
número estimado.

- Fecha de ejecución: 2026-09-15
- Ejecutado por: Claude Code (agente), a pedido de Eduardo Rodas Arias
- Método de acceso al entorno: SSH contra gateway `10.20.12.153` (confirmado por
  Eduardo en esta sesión), reenvío de puertos por nodo según `acceso-vnrt.md`.
  Autenticación por llave dedicada `vnrt_ed25519` instalada en los 8 nodos durante
  esta sesión (antes solo había contraseña).
- Commit del repo en el momento de medir: `28c3166` (fases 1 y 3);
  continuación (Paso 0 y Fase 2) sobre `43d7894`.

**Historial de corridas:**
- Corrida 1 (2026-09-15): fases 1 y 3, solo lectura.
- Corrida 2 (2026-09-15): Paso 0 (habilitar OF1.3) y Fase 2 (capacidad del
  plano de datos), siguiendo `01-preparacion-y-pruebas.md`, con luz verde de
  Eduardo para los cambios de escritura de ese runbook. Fases 4 y 5 pendientes.

## Fase 1. Inventario

### Identidad de cada nodo (`hostname; whoami; id`)

| Nodo | Puerto SSH | hostname | Usuario | Grupos relevantes |
|---|---|---|---|---|
| controller | 5800 | controller | ubuntu | sudo, adm, lxd |
| sw1 | 5801 | sw1 | ubuntu | sudo, adm, lxd |
| sw2 | 5802 | sw2 | ubuntu | sudo, adm, lxd |
| sw3 | 5803 | sw3 | ubuntu | sudo, adm, lxd |
| h1 | 5811 | h1 | ubuntu | sudo, adm, lxd |
| h2 | 5812 | h2 | ubuntu | sudo, adm, lxd |
| h3 | 5813 | h3 | ubuntu | sudo, adm, lxd |
| h4 | 5814 | h4 | ubuntu | sudo, adm, lxd |

Ninguno de los 8 nodos tiene al usuario `ubuntu` en un grupo con acceso directo al
socket de OVS (`/var/run/openvswitch/db.sock`, modo `srwxr-x---` root:root). Todos
los comandos `ovs-*` necesitan `sudo`.

### Direccionamiento observado (`ip -br a`)

| Nodo | Interfaz gestión (192.168.0.0/24) | Interfaz de datos / control |
|---|---|---|
| controller | ens3 = 192.168.0.10 | ens4 = 172.16.0.1/24 |
| sw1 | ens3 = 192.168.0.11 | ens4/5/6 sin IP (enclavadas a OVS); bridge `sw1` = 172.16.0.1/24 |
| sw2 | ens3 = 192.168.0.12 | ens4/5/6 sin IP; bridge `sw2` = 172.16.0.2/24 |
| sw3 | ens3 = 192.168.0.13 | ens4/5/6 sin IP; bridge `sw3` = 172.16.0.3/24 |
| h1 | ens3 = 192.168.0.21 | ens4 = 10.0.0.1/24 |
| h2 | ens3 = 192.168.0.22 | ens4 = 10.0.0.2/24 |
| h3 | ens3 = 192.168.0.23 | ens4 = 10.0.0.3/24 |
| h4 | ens3 = 192.168.0.24 | ens4 = 10.0.0.4/24 |

**Hallazgo:** `controller:ens4` y el puerto interno del bridge `sw1` tienen
**la misma dirección IP** (172.16.0.1/24). Ver detalle en "Hallazgos que afectan
el diseño".

### Máquina (`uname -a`, `nproc`, `free -h`, `df -h /`)

| Nodo | Kernel | vCPU | RAM total | Disco `/` disponible |
|---|---|---|---|---|
| controller | 6.8.0-139-generic, Ubuntu 24.04 LTS | 2 | 1.9Gi | 2.4G de 5.9G (57%) |
| sw1 | 6.8.0-139-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.4G de 5.9G (57%) |
| sw2 | 6.8.0-138-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.4G de 5.9G (57%) |
| sw3 | 6.8.0-138-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.4G de 5.9G (57%) |
| h1 | 6.8.0-139-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.5G de 5.9G (57%) |
| h2 | 6.8.0-139-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.4G de 5.9G (57%) |
| h3 | 6.8.0-138-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.5G de 5.9G (57%) |
| h4 | 6.8.0-138-generic, Ubuntu 24.04 LTS | 1 | 961Mi | 2.3G de 5.9G (60%) |

CPU en todos: Intel Core Processor (Broadwell, IBRS), virtualizado. El
`controller` es el único nodo con 2 vCPU y ~2x la RAM del resto — relevante para
la fase 4 (techo de Packet-In/s), pendiente.

Nota: hay dos imágenes de kernel distintas en el parque (`-138` y `-139`), sin
patrón claro por rol. No parece afectar el diseño, se deja anotado.

### Open vSwitch (`sw1`, `sw2`, `sw3`; requiere `sudo`)

| Dato | Valor |
|---|---|
| Versión de OVS | 3.3.9 (igual en los 3 switches) |
| Versión de ovs-ofctl | 3.3.9, reporta soportar OpenFlow versions `0x1:0x6` (OF1.0 a OF1.5) |
| Bridges existentes | uno por switch: `sw1`, `sw2`, `sw3` (nombre = hostname) |
| Datapath type | `system` (kernel), no `netdev`/DPDK |
| **Protocolos negociados por bridge** | **`[OpenFlow10]` únicamente**, en los 3 bridges |
| Fail mode | `secure` en los 3 |
| Reglas ya instaladas | 0 en los 3 (no hay controlador conectado actualmente) |
| Tabla de fdb (`fdb/show`) | vacía en los 3, antes y después de generar tráfico de prueba |

Comando: `sudo ovs-vsctl get bridge <br> datapath_type protocols fail_mode` y
`sudo ovs-vsctl show`.

**Hallazgo crítico:** aunque el binario `ovs-ofctl` soporta hasta OpenFlow 1.5,
**cada bridge está configurado en la base de datos de OVS para negociar solo
OpenFlow 1.0** (`protocols: [OpenFlow10]`). Al intentar `ovs-ofctl -O OpenFlow13
show <br>` (incluso local, contra el socket de gestión), OVS rechaza la
conexión:

```
vconn|WARN|unix:/var/run/openvswitch/sw1.mgmt: version negotiation failed
(we support version 0x04, peer supports version 0x01)
ovs-ofctl: sw1: failed to connect to socket (Protocol error)
```

Esto significa que, **tal como están configurados hoy los tres bridges reales
de la topología**, un controlador Ryu que hable OpenFlow 1.3 (como asume
`docs/contratos/tablas-openflow.md`: multitabla, `metadata`, `goto_table`) **no
podría completar el handshake** contra `sw1`, `sw2` ni `sw3`. El problema no es
de soporte (OVS 3.3.9 sí soporta OF1.3+), es de configuración: falta
`ovs-vsctl set bridge <br> protocols=OpenFlow13` en cada uno. Ese es un cambio
de escritura, fuera del alcance de esta corrida de solo lectura — se deja como
hallazgo para el ADR 0001 y no se aplicó.

`dump-meter-features` y `dump-group-features` tampoco se pudieron probar contra
los bridges reales por el mismo motivo de negociación de versión (piden
OpenFlow13 explícitamente). La fase 2 sí los probó exitosamente contra un
bridge temporal `bench0` recién creado — pendiente de ejecutar en esta sesión.

Puertos por bridge, vistos vía `sudo ovs-dpctl show` (número de puerto interno
del datapath, no necesariamente igual al puerto OpenFlow, que no se pudo leer
por el problema anterior):

| Switch | port 1 | port 2 | port 3 (internal) | port 4 |
|---|---|---|---|---|
| sw1 | ens5 | ens6 | sw1 | ens4 |
| sw2 | ens5 | ens6 | sw2 | ens4 |
| sw3 | ens5 | ens6 | sw3 | ens4 |

### Controladores presentes (nodo `controller`)

| Controlador | Instalado | Versión |
|---|---|---|
| Ryu (`ryu-manager`) | No | — |
| ONOS / karaf | No | — |
| OpenDaylight | No | — |
| Faucet / gauge | No | — |
| POX / NOX | No | — |
| Python3 | Sí | 3.12.3 |
| `/opt` | (vacío o no existe) | — |

**Hallazgo:** el nodo `controller` no tiene Ryu instalado ni ningún otro
controlador SDN. `pip3` tampoco está instalado (`pip3 list` no corrió en ningún
nodo). Antes de poder ejecutar la fase 4 (medición de Packet-In) hay que
instalar Ryu — lo cual requiere confirmar con el equipo si se instala vía `apt`,
`pip` (necesita instalar `pip3` primero) o un entorno virtual, y **pedir permiso
antes de instalar nada**, como exige la regla 7 de `CLAUDE.md`.

### Herramientas de prueba (los 8 nodos)

| Herramienta | controller | sw1/sw2/sw3 | h1 | h2 | h3 | h4 |
|---|---|---|---|---|---|---|
| nmap | NO | NO | NO | NO | NO | NO |
| hping3 | NO | NO | NO | NO | NO | NO |
| iperf3 / iperf | NO | NO | NO | NO | NO | NO |
| tcpdump | Sí | Sí | Sí | Sí | Sí | Sí |
| tshark | NO | NO | NO | NO | NO | NO |
| mausezahn | NO | NO | NO | NO | NO | NO |
| ping | Sí | Sí | Sí | Sí | Sí | Sí |
| arping | NO | NO | Sí | NO | NO | NO |
| python3 | Sí (3.12.3) | Sí | Sí | Sí | Sí | Sí |
| pip3 | NO | NO | NO | NO | NO | NO |
| scapy | NO | NO | NO | NO | NO | NO |
| cbench | NO | NO | NO | NO | NO | NO |
| git / tmux / jq / bc / curl | Sí | Sí | Sí | Sí | Sí | Sí |

**Hallazgo:** ninguno de los 8 nodos trae `nmap`, `hping3`, `scapy` ni `cbench`
preinstalados. La fase 5 (banco de ataques para R3) y la fase 4 (comparación con
`cbench`) tal como están escritas en el runbook **no se pueden ejecutar sin
instalar paquetes primero**, lo cual requiere pedir permiso explícito (regla 7
de `CLAUDE.md` y regla 7 del propio runbook). Sin `pip3` tampoco se puede
instalar `scapy` ni `p4runtime-shell` vía pip sin antes resolver eso.

### Topología existente: namespaces (`ip netns list`)

**En los 8 nodos, `ip netns list` no devuelve ningún namespace.** No hay `veth`
ni interfaces con nombre `ovs` fuera de las ya inventariadas en los switches.

**Hallazgo importante para la fase 5:** el runbook (`00-reconocimiento-vnrt.md`)
y el bloque de ataques asumen comandos como `ip netns exec atacante nmap ...` o
`ip netns exec h1 ...`. **Eso no aplica a este VNRT**: `h1`–`h4` no son
namespaces dentro de una máquina compartida, son **VMs independientes**, cada
una alcanzada por su propio puerto SSH (confirmado también en
`acceso-vnrt.md`). Cuando se ejecute la fase 5, los comandos de ataque deben
correr **directamente en la shell del host que haga de atacante** (por ejemplo
`h4`), sin el prefijo `ip netns exec`.

## Mapa real de topología (dato central de esta corrida)

El diagrama preliminar de `acceso-vnrt.md` asumía una cadena `sw1—sw2—sw3` con
`sw2` como switch central y **h2 colgando de sw1**. Se verificó puerto por
puerto con dos métodos de solo lectura:

1. `ip -d link show` en cada switch, para confirmar qué interfaces están
   enclavadas al datapath OVS (`master ovs-system`) — confirma que en los 3
   switches, `ens4`, `ens5` y `ens6` son puertos de datos, y `ens3` es la red de
   gestión, separada.
2. **Correlación de contadores** (`ip -s link show <if>`, campo RX packets),
   tomando una foto antes y después de mandar 5 pings broadcast
   (`ping -b -c 5 -I ens4 <broadcast>`) desde la interfaz de datos de cada host
   y del controller. Como los switches están en `fail_mode=secure` con 0 reglas
   instaladas, el tráfico no se reenvía a ningún otro puerto — solo incrementa
   el contador del puerto de ingreso directo, lo que permite identificarlo sin
   tocar ninguna configuración de OVS.

| Origen | Comando | Puerto que subió en +5 | Switch/puerto real |
|---|---|---|---|
| controller (172.16.0.1, ens4) | `ping -b -c5 -I ens4 172.16.0.255` | sw1 ens4: 1513→1518 | **controller — sw1/ens4** |
| h1 (10.0.0.1) | `ping -b -c5 -I ens4 10.0.0.255` | sw2 ens5: 1495→1500 | **h1 — sw2/ens5** |
| h2 (10.0.0.2) | `ping -b -c5 -I ens4 10.0.0.255` | sw2 ens6: 1404→1409 | **h2 — sw2/ens6** |
| h3 (10.0.0.3) | `ping -b -c5 -I ens4 10.0.0.255` | sw3 ens5: 1280→1285 | **h3 — sw3/ens5** |
| h4 (10.0.0.4) | `ping -b -c5 -I ens4 10.0.0.255` | sw3 ens6: 1240→1245 | **h4 — sw3/ens6** |

Tabla resultante, la que necesita R3 para la detección de IP spoofing
(IP + MAC + puerto de ingreso):

| Nodo | MAC (ens4, la de datos) | Switch de acceso | Puerto del switch |
|---|---|---|---|
| controller | fa:16:3e:77:ae:92 | sw1 | ens4 |
| h1 | fa:16:3e:9f:b2:02 | sw2 | ens5 |
| h2 | fa:16:3e:bb:e9:aa | sw2 | ens6 |
| h3 | fa:16:3e:ef:46:b7 | sw3 | ens5 |
| h4 | fa:16:3e:35:f5:89 | sw3 | ens6 |

Con esto, cada switch tiene exactamente un puerto libre: `sw1/ens5`,
`sw1/ens6`, `sw2/ens4` y `sw3/ens4`. Por descarte, estos son los enlaces entre
switches (`sw1—sw2` y `sw1—sw3`), es decir **`sw1` parece ser el switch
central** (conecta a controller, sw2 y sw3), no `sw2` como asumía el diagrama
preliminar.

**No se pudo confirmar cuál puerto de `sw1` (`ens5` o `ens6`) va a `sw2` y
cuál va a `sw3`.** Motivo: esos puertos no tienen IP propia (están enclavados al
datapath OVS sin dirección), no hay LLDP instalado en ningún nodo, no hay
controlador ni reglas que permitan inundar tráfico de prueba entre switches
sin generar una regla nueva, y el fdb quedó vacío incluso después de las
pruebas de tráfico (`fail_mode=secure` con 0 reglas no aprende MACs). Queda como
prueba pendiente — se resolvería instalando LLDP (paquete nuevo, requiere
permiso) o con un controlador real conectado en la fase 4.

## Fase 3. Viabilidad de P4 (solo lectura)

Ejecutado en los 8 nodos (`command -v` para binarios, `dpkg -l` para paquetes,
`find / -iname '*tofino*'`).

| Componente | controller | sw1 | sw2 | sw3 | h1–h4 |
|---|---|---|---|---|---|
| bmv2 / simple_switch / simple_switch_grpc / simple_switch_CLI | NO | NO | NO | NO | NO |
| p4c / p4c-bm2-ss | NO | NO | NO | NO | NO |
| psa_switch / bf_switchd | NO | NO | NO | NO | NO |
| Paquetes `p4`/`bmv2`/`behavioral-model` (`dpkg -l`) | ninguno | ninguno | ninguno | ninguno | ninguno |
| p4runtime-shell (Python) | NO | NO | NO | NO | NO |
| Rastro de Tofino (`find / -iname '*tofino*'`) | ninguno | ninguno | ninguno | ninguno | ninguno |

**Conclusión para el ADR 0001 (dato, no decisión):** no se encontró ningún
componente de la cadena de herramientas P4 (compilador, switch de software
`bmv2`, shell de P4Runtime) ni rastro de acceso a hardware o modelo Tofino en
ninguno de los 8 nodos del VNRT. Según la tabla de decisión del propio runbook
(`00-reconocimiento-vnrt.md`, fase 3), este hallazgo corresponde al primer caso:
la vía P4/Tofino (opción B del AVZ01) no está disponible en este entorno tal
como está aprovisionado hoy. La decisión formal de cerrar el ADR 0001 con esto
le corresponde a Eduardo como arquitecto de solución, no se edita el ADR en
esta corrida.

## Paso 0. Habilitar OpenFlow 1.3 en los tres switches (corrida 2)

Cambio de escritura autorizado por Eduardo, siguiendo `01-preparacion-y-pruebas.md`.
Resuelve el hallazgo crítico de la corrida 1 (los bridges solo negociaban OF1.0).

Respaldo previo (regla 3): en los 3 switches, `protocols=[OpenFlow10]` y
`dump-flows` = 0 antes del cambio. Guardado en el scratchpad de la sesión.

Comando aplicado en cada switch (`sw1`, `sw2`, `sw3`), vía SSH con `sudo`:

```bash
sudo ovs-vsctl set bridge <swN> protocols=OpenFlow13
sudo ovs-vsctl get bridge <swN> protocols      # -> [OpenFlow13]
sudo ovs-ofctl -O OpenFlow13 show <swN>         # ahora responde
```

Resultado: en los 3, `protocols` pasó a `[OpenFlow13]` y `ovs-ofctl -O
OpenFlow13 show` ya completa el handshake (antes fallaba con "version
negotiation failed"). **`dump-flows` sigue en 0** en los 3 tras el cambio: no se
instaló ninguna regla, solo se cambió la versión negociada. El cambio es
reversible con `set bridge <swN> protocols=OpenFlow10`.

Datos nuevos que este cambio deja ver (`ovs-ofctl -O OpenFlow13 show`):

| Switch | dpid | n_tables | Puertos OpenFlow (nº → interfaz) |
|---|---|---|---|
| sw1 | `0000a223f2c04547` | 254 | 1→ens4 (controller), 2→ens5, 3→ens6, LOCAL→sw1 |
| sw2 | `00001a749039894a` | 254 | 1→ens4, 2→ens5 (h1), 3→ens6 (h2), LOCAL→sw2 |
| sw3 | `0000ca272d265744` | 254 | 1→ens6 (h4), 2→ens5 (h3), 3→ens4, LOCAL→sw3 |

Notas:
- **254 tablas** por bridge: el pipeline multitabla del contrato
  (`docs/contratos/tablas-openflow.md`) cabe de sobra.
- En `sw3` la numeración OpenFlow **no** sigue el orden de `ensN`: puerto OF 1 =
  ens6, 3 = ens4. Al escribir reglas hay que usar el número OpenFlow, no asumir
  que `ens4`=1. Los `dpid` de arriba son los que reportará cada switch al
  conectarse al controlador en la fase 4.

## Fase 2. Capacidad del plano de datos (corrida 2)

Ejecutada sobre un bridge temporal `bench0` creado en `sw1`, aislado de la
topología real (sin puertos físicos enclavados). Se creó, se midió y se eliminó
en la misma corrida; ver limpieza al final de la sección. `sw1` se verificó
intacto después (sigue en OF13, 0 flujos, sus 3 puertos de datos).

### 2.1 Versiones de OpenFlow soportadas

Se habilitaron todas las versiones en `bench0` y se probó el handshake con cada
una (`ovs-ofctl -O OpenFlowXX show bench0`):

| Versión | Soportada |
|---|---|
| OpenFlow 1.0 | Sí |
| OpenFlow 1.1 | Sí |
| OpenFlow 1.2 | Sí |
| OpenFlow 1.3 | Sí |
| OpenFlow 1.4 | Sí |
| OpenFlow 1.5 | Sí |

El build de OVS 3.3.9 soporta OF1.0 a 1.5. El pipeline multitabla del contrato
(`docs/contratos/tablas-openflow.md`) requiere 1.3 y está cubierto de sobra. La
limitación de la corrida 1 era de configuración por bridge, no del build (se
resolvió en el Paso 0).

### 2.2 Funciones que necesita el diseño

| Función | Soportada | Evidencia |
|---|---|---|
| Múltiples tablas y `goto_table` | **Sí** | `add-flow "table=0,...,goto_table:1"` aceptado; `n_tables=254` |
| `write_metadata` | **Sí** | misma regla instalada OK: `actions=write_metadata:0x1/0xf,goto_table:1` |
| **Meters** | **Sí** | `add-meter "meter=1,kbps,band=type=drop,rate=1000"` aceptado; `dump-meters` lo lista |
| Grupos | **Sí** | `dump-group-features` reporta tipos `all/select/indirect/fast failover`, `max_groups≈0xffffff00` |

**Resultado crítico para R3: los meters SÍ están soportados.** La escalera de
mitigación de R3 (rate-limit con meters) es implementable tal como está en el
diseño; **no** hace falta rediseñarla con colas de QoS ni abrir el ADR de
rediseño que contemplaba el runbook. Los grupos `fast failover` también están
disponibles por si se necesitan más adelante.

Nota de herramienta (no afecta el diseño): en OVS 3.3.9 el subcomando
`ovs-ofctl dump-meter-features` devuelve "unknown command". Es un cambio de CLI,
no una ausencia de soporte: `add-meter` y `dump-meters` funcionan sin problema.
Para leer las capacidades de meters se usa `dump-meters`/`meter-stats` en esta
versión.

### 2.3 Escala y velocidad de instalación de reglas

Reglas únicas `priority=100,ip,nw_src=10.a.b.c,actions=drop` cargadas en lote con
`ovs-ofctl add-flows` sobre `bench0` (OF13). Tiempo con `date +%s.%N`:

| N reglas | Instaladas | Rechazos | Tiempo total | Tiempo por regla |
|---|---|---|---|---|
| 100 | 100 | 0 | 0.054 s | 543 µs |
| 1 000 | 1 000 | 0 | 0.191 s | 191 µs |
| 5 000 | 5 000 | 0 | 0.721 s | 144 µs |
| 20 000 | 20 000 | 0 | 2.823 s | 141 µs |
| 50 000 | 50 000 | 0 | 7.247 s | 144 µs |

**Punto donde empieza a degradarse:** no se observó degradación por regla hasta
50 000. El costo por regla *baja* de 543 µs (N=100) a ~140 µs y se **estabiliza
plano** a partir de N≈5 000 (~140-145 µs/regla, ≈7 000 reglas/s). El valor alto
en N=100 es costo fijo de arranque del lote amortizado sobre pocas reglas, no
degradación.

**Máximo de reglas aceptado antes de error:** OVS aceptó las 50 000 sin rechazar
ninguna (`rc=0`, instaladas=N en todos los puntos). No se buscó el techo
absoluto porque 50 000 ya excede en varios órdenes de magnitud lo que instalaría
la solución.

Lectura para la rúbrica (escalabilidad): en OVS por software el costo de
instalación es **lineal y plano por regla**, sin el tope duro de una TCAM de
hardware. Esto **contrasta** con el presupuesto de TCAM (cálculo analítico para
hardware, peso 10 en R2): son dos cosas distintas y hay que presentarlas por
separado, como advierte el runbook. El dato de OVS no sustituye la estimación de
TCAM; sí sustenta que el prototipo no tiene problema de capacidad de tabla.

### 2.4 Latencia según tamaño de tabla

**No ejecutada.** `bench0` es un bridge aislado sin hosts conectados, y montar
dos endpoints (puertos internos + direccionamiento) para medir RTT excede lo que
pide la Fase 2 de `01-preparacion-y-pruebas.md`, que no lista esta sub-prueba. Se
puede medir mejor en la Fase 4, con el controlador conectado y tráfico real entre
hosts. Queda anotada como pendiente, no como dato inventado.

### 2.5 Limpieza

`del-flows bench0` + `del-br bench0` ejecutados. Confirmado: `ovs-vsctl list-br`
solo devuelve `sw1`; `bench0` ya no aparece. Ninguna regla ni bridge de la
topología real fue tocado.

## Fase 4. Cuello de botella del controlador (corrida 3, en curso)

### 4.0 Instalación planificada (registro previo, autorizada por Eduardo)

Antes de instalar nada se deja constancia de qué se va a instalar y con qué
comando, en el nodo `controller` (2 vCPU, 1.9 GiB RAM, Ubuntu 24.04, Python
3.12.3, sin Ryu ni pip):

```bash
# en controller
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
python3 -m venv ~/ryu-venv
source ~/ryu-venv/bin/activate
pip install --upgrade pip
pip install ryu            # si eventlet choca con Python 3.12, fallback: pip install os-ken
```

Motivo: la Fase 4 mide el techo de Packet-In/s del controlador, dato del que
depende el diseño de detección de R3. Se usa un entorno virtual (`~/ryu-venv`)
para no tocar el Python del sistema. Se avisará al coach que el entorno se
modifica, por si el VNRT se reaprovisiona.

**Resultado de la instalación (ejecutado 2026-09-15):**

- `apt`/`sudo` **no se usaron**: el `sudo` de `controller` pide contraseña (solo
  se configuró NOPASSWD para `ovs-*` en los switches). Para no tocar el sistema
  compartido, el venv se creó con `python3 -m venv --without-pip ~/ryu-venv` y
  pip se bootstrapeó desde la fuente oficial `https://bootstrap.pypa.io/get-pip.py`.
  Todo queda dentro de `~/ryu-venv`, reversible con `rm -rf ~/ryu-venv`. pip
  26.2.1, Python 3.12.3.
- **`pip install ryu` FALLA** en Python 3.12: el `setup.py` de Ryu usa
  `easy_install.get_script_args`, API que setuptools moderno ya eliminó
  (`AttributeError: 'types.SimpleNamespace' object has no attribute
  'get_script_args'`). Es la incompatibilidad conocida que el runbook anticipa.
- **`pip install os-ken` OK**: os-ken 4.2.2 (con eventlet 0.41.2, compatible con
  3.12). **Este es el controlador que queda funcionando.** Implicación para el
  código del proyecto: los imports son `os_ken.*`, no `ryu.*` (equivalentes uno
  a uno). Anotado también en el ADR de controlador.
- **Salvedad de empaquetado:** el wheel de os-ken 4.2.2 en PyPI **no incluye el
  módulo `os_ken.cmd`** ni registra el console-script `osken-manager`, así que no
  hay comando lanzador. La API interna (`os_ken.base.app_manager`,
  `os_ken.controller.controller.OpenFlowController`, `os_ken.lib.hub`) sí está
  completa y espeja la de Ryu, por lo que se usa un lanzador propio mínimo
  (`tools/osken_run.py`) que hace lo mismo que `ryu-manager` por dentro
  (cargar la app, crear contextos, instanciar y levantar el `OpenFlowController`).
  La clase base de las apps es `app_manager.OSKenApp`.

### 4.1 App de medición y montaje

- App: `tools/bench_packetin.py` (`PacketInBench`, subclase de `OSKenApp`, OF1.3).
  Cuenta Packet-In, imprime PPS por segundo, mide CPU propia leyendo
  `/proc/self/stat`, y cronometra la latencia Packet-In→FLOW_MOD confirmado
  enviando, cada 200 Packet-In, un `FLOW_MOD` no-op (matchea un `udp_dst` que el
  generador nunca usa, sin acciones = drop, no toca el tráfico) seguido de un
  `OFPBarrierRequest`; la latencia es el RTT hasta el `BarrierReply`. La **única**
  regla de reenvío que instala es el table-miss → CONTROLLER (necesario en OF1.3).
- Lanzador: `tools/osken_run.py` (por la salvedad de empaquetado de 4.0).
- Canal de control: el controlador escucha en `0.0.0.0:6653`. Se conectó **`sw2`**
  (dpid `00001a749039894a`, con `h1` y `h2` colgando) por la **red de gestión**:
  `sudo ovs-vsctl set-controller sw2 tcp:192.168.0.10:6653`. Handshake OK, el
  table-miss quedó instalado en sw2. Esto confirma que **el canal OpenFlow va por
  la red de gestión (192.168.0.0/24), no por la red 172.16.0.0/24** (los switches
  no alcanzan `172.16.0.1` por el plano de datos sin flujos). Resuelve en parte el
  enigma de la IP duplicada 172.16.0.1: esa red no se usa para el canal de control.
- Generador de carga: `tools/loadgen_packetin.py`, stdlib pura (sin root ni
  scapy, que no se pudieron usar porque los hosts no tienen sudo sin contraseña).
  Envía UDP a la dirección de broadcast del plano de datos (`10.0.0.255`); cada
  trama hace table-miss → un Packet-In. Corre directo en la shell del host (sin
  `ip netns`).

### 4.2 y 4.3 Medición: rampa de carga y saturación

Rampa de tasa objetivo desde `h1` (8 s por punto), más ilimitado desde `h1` y
desde `h1`+`h2` en paralelo para forzar saturación. Cada línea del monitor
reporta PPS del segundo, CPU del proceso (base 100% = un núcleo; os-ken es
monohilo por eventlet, el nodo tiene 2 vCPU) y la distribución acumulada de
latencia Packet-In→FLOW_MOD.

| Tasa ofrecida | PPS procesados (sostenido) | Pérdida | CPU controlador | Latencia mediana | Latencia p95 |
|---|---|---|---|---|---|
| 100 pps | ~100 | 0 | ~4 % | 1.45 ms | 1.45 ms |
| 500 pps | ~500 | 0 | ~17-20 % | ~1.2 ms | ~1.56 ms |
| 1 000 pps | ~1 000 | 0 | ~32-34 % | ~0.95 ms | ~1.5 ms |
| 2 000 pps | ~2 000 | 0 | ~47-52 % | ~0.91 ms | ~1.5 ms |
| 4 000 pps | ~4 000 | 0 | ~53-67 % | ~0.87 ms | ~1.6 ms |
| ilimitado (h1 ~93k pps ofrecidos) | **~11 000-11 700 (techo)** | sí, masiva | **~110-112 % (núcleo saturado)** | ~0.9-1.2 ms | **175 → 540 → 1290 → 4100 ms** |
| ilimitado (h1+h2 ~185k pps ofrecidos) | ~11 000 (mismo techo) | sí, masiva | ~110 % | **sube a ~2650 ms** | ~4130 ms |

**Punto de saturación observado:** ~**11 000 Packet-In/s sostenidos**. En ese
punto un núcleo queda al 100 % (CPU del proceso ~110 %), el switch/kernel empieza
a **descartar** Packet-In (se ofrecieron 93 000 pps y solo se procesaron ~11 000),
y la **cola de Packet-In se acumula**: la latencia p95 se dispara de ~1.6 ms a
>4 s. La mediana se mantiene baja hasta que la saturación es total (h1+h2), donde
también colapsa a segundos.

**Comparación con los compromisos del AVZ02:**

| Métrica | Compromiso AVZ02 | Medido | Margen |
|---|---|---|---|
| Latencia de detección (p95 PktIn→FlowMod) | ≤ 500 ms | 1.45 ms @ 100 flujos/s; se mantiene <2 ms hasta ~4 000 pps | **holgadísimo** por debajo de saturación |
| CPU del controlador bajo 100 flujos/s | ≤ 60 % | ~4 % | **holgadísimo** |
| (referencia) CPU al 60 % | — | se cruza cerca de ~4 000-5 000 pps | — |
| (referencia) p95 cruza 500 ms | — | solo al saturar (~11 000 pps) | — |

**Lectura para el HLD de R3:** el controlador aguanta ~11 000 Packet-In/s antes
de degradarse, y hasta ~4 000 pps se mantiene bajo el 60 % de CPU con latencia
sub-2 ms. Eso está **muy por encima** de los 100 flujos/s comprometidos: hay
margen amplio. Pero define el techo: si la detección de R3 se basa en contar
Packet-In en el controlador, por encima de ~11 000 pps se pierden eventos y la
latencia se vuelve inservible. Un atacante que genere un flood de Packet-In
(p. ej. `hping3 --flood`, Fase 5) puede empujar hacia esa zona; el diseño de R3
debe contemplar rate-limiting en el plano de datos (los meters de la Fase 2, que
sí están soportados) para no depender solo del plano de control bajo ataque.

### 4.4 Comparación con otra alternativa

Pendiente. No se instaló un segundo controlador (p. ej. una app equivalente en
otro runtime) ni `cbench` (no está en el entorno; instalarlo requiere `apt`, que
en `controller` pide contraseña). Para "elección fundamentada" del ADR, la
comparación puede completarse citando cifras publicadas de Ryu/os-ken vs. otros
controladores, **dejando claro que son de la literatura y no medidas aquí**. No
se presenta ningún número inventado.

### 4.5 Limpieza

`sudo ovs-vsctl del-controller sw2` y `del-flows sw2` ejecutados. `sw2` quedó sin
controlador, en `[OpenFlow13]` (estado del Paso 0) y con 0 flujos. El controlador
os-ken se detuvo (sesión tmux cerrada, puertos 6653/6633 liberados). El venv
`~/ryu-venv` y los scripts en `~/bench` del nodo `controller` quedan instalados
para futuras corridas (reversible con `rm -rf`).

## Fase 5. Banco de ataques (corrida 4, en curso)

### 5.0 Instalación planificada (registro previo, autorizada en `01-preparacion-y-pruebas.md`)

Roles para esta corrida: **`h4` como atacante** (sw3), **`h1` como objetivo**
(sw2). El tráfico cruza `sw1`, que es donde conviene observar la detección,
siguiendo la sugerencia del runbook de continuación.

Verificado antes de instalar: los 4 hosts piden contraseña de `sudo` (no hay
NOPASSWD configurado en ellos, a diferencia de los switches) y ninguno trae
`nmap`, `hping3`, `iperf3` ni `scapy`.

Comandos a ejecutar (registrados antes de correrlos, como exige la regla de
`01-preparacion-y-pruebas.md`):

```bash
# en h4 (atacante)
sudo apt-get update
sudo apt-get install -y nmap hping3 python3-scapy

# en h1 (objetivo, para medir tráfico legítimo / falsos positivos)
sudo apt-get install -y iperf3
```

Motivo: son las herramientas mínimas que pide la Fase 5 para generar los seis
escenarios (network scanning, port scanning rápido y lento, IP spoofing, flood
muchos-a-uno, tráfico legítimo) y medir la firma que cada uno deja en los
Packet-In del controlador. Sin esto, los umbrales de R3 (T, N_dst, N_port,
N_miss) y las métricas de ≥95% de R1/R2 no se pueden medir, solo declarar como
pendientes.

**Resultado de la instalación (ejecutado 2026-09-17):**

| Nodo | Paquete | Versión |
|---|---|---|
| h4 | nmap | 7.94SVN |
| h4 | hping3 | 3.0.0-alpha-2 |
| h4 | python3-scapy | 2.5.0 |
| h1 | iperf3 | 3.16 (cJSON 1.7.15) |

`iperf3` en `h1` se dejó **sin arrancar como daemon** (respuesta "No" al
debconf de arranque automático): se levanta manualmente con `iperf3 -s` solo
durante la prueba de tráfico legítimo, para no dejar un servicio escuchando
permanentemente en un nodo compartido del curso.

**Ajuste sobre la marcha:** el plan original solo instaló `iperf3` en el
objetivo (`h1`, servidor). El cliente (`h2`) también necesita el binario
(`iperf3 -c`), y no se había registrado. Se instala con el mismo comando:
`sudo apt-get install -y iperf3` en `h2`.

## Hallazgos que afectan el diseño

1. ~~**Los tres bridges reales (`sw1`, `sw2`, `sw3`) están configurados solo con
   `protocols=[OpenFlow10]`.**~~ **RESUELTO en la corrida 2 (Paso 0):** los 3
   bridges quedaron en `protocols=[OpenFlow13]` y ya completan el handshake OF1.3.
   El cambio es reversible. Ver la sección "Paso 0".
2. **El diagrama preliminar de topología de `acceso-vnrt.md` estaba
   parcialmente equivocado.** El switch central es `sw1` (conecta a controller,
   sw2 y sw3), no `sw2`. `h2` cuelga de `sw2`, no de `sw1`. Se corrigió la tabla
   de acceso arriba; falta actualizar el diagrama de `acceso-vnrt.md` y el
   futuro documento de arquitectura.
3. **La fase 5 del runbook no es ejecutable tal como está escrita**: no hay
   namespaces (`ip netns`) en este VNRT, cada host es una VM real con su propio
   puerto SSH. Hay que reescribir los comandos de ataque sin `ip netns exec`.
4. **Ningún nodo trae herramientas de prueba/ataque preinstaladas**
   (`nmap`, `hping3`, `scapy`, `cbench`, ni `pip3`). La Fase 4 se resolvió sin
   ellas (generador stdlib propio); la Fase 5 sigue bloqueada hasta instalar
   `nmap`/`hping3`/`scapy` en el host atacante. Además **los hosts no tienen sudo
   sin contraseña**, así que la generación de tráfico de la Fase 4 se hizo sin
   root (broadcast UDP), y la Fase 5 necesitará resolver el tema de privilegios
   para las herramientas que piden raw sockets.
5. **`controller:ens4` y el puerto interno del bridge `sw1` comparten la misma
   IP (172.16.0.1/24).** Parcialmente aclarado en la Fase 4: **el canal OpenFlow
   controlador↔switch va por la red de gestión (192.168.0.0/24), no por
   172.16.0.0/24**, que no se usa para el control (los switches ni siquiera
   alcanzan 172.16.0.1 por el plano de datos sin flujos). La IP duplicada en
   172.16 no afecta el canal de control. Queda por confirmar con el staff para
   qué se pensaba usar esa red y si la duplicación es intencional.
6. ~~**No hay Ryu instalado en `controller`.**~~ **RESUELTO en la corrida 3:**
   Ryu no instala en Python 3.12, quedó **os-ken 4.2.2** en un venv. Implicación
   de diseño: el código del proyecto usa imports `os_ken.*` y un lanzador propio
   (`tools/osken_run.py`). Ver Fase 4.0.
7. **No se pudo determinar el emparejamiento exacto sw1–sw2 y sw1–sw3** (qué
   puerto de `sw1` va a cuál). Sigue pendiente; se resolverá con
   `os_ken.topology` (descubrimiento por LLDP) conectando los 3 switches, o con
   un controlador de reenvío real. Ver detalle en "Mapa real de topología".
8. **Techo del plano de control medido: ~11 000 Packet-In/s** (un núcleo al
   100 %). Muy por encima de los 100 flujos/s comprometidos, pero define el
   límite bajo ataque de flood: R3 no debe depender solo de contar Packet-In en
   el controlador; conviene rate-limiting en el plano de datos con meters (que la
   Fase 2 confirmó soportados). Ver Fase 4.2/4.3.

## Pruebas que no se pudieron ejecutar

| Prueba | Motivo |
|---|---|
| ~~`ovs-ofctl -O OpenFlow13 show` en sw1/sw2/sw3~~ | RESUELTO en corrida 2 (Paso 0): los bridges ya negocian OF1.3 |
| ~~`dump-*-features` de meters/grupos~~ | RESUELTO en corrida 2 (Fase 2): meters y grupos probados OK en `bench0` |
| ~~Fase 2 (capacidad del plano de datos)~~ | RESUELTO en corrida 2: ejecutada completa sobre `bench0` |
| Emparejamiento exacto de puertos sw1↔sw2 y sw1↔sw3 | Aún pendiente: sin controlador conectado ni reglas, el fdb no aprende (`fail_mode=secure`, 0 flujos). Se resolverá en la Fase 4 con el controlador conectado, o instalando LLDP |
| LLDP como método de mapeo de adyacencias | `lldpd`/`lldpcli` no están instalados en ningún nodo |
| Latencia RTT según tamaño de tabla (2.4) | `bench0` no tiene hosts conectados; se medirá mejor en la Fase 4 con tráfico real |
| ~~Instalar el controlador~~ | RESUELTO en corrida 3: os-ken 4.2.2 en venv (Ryu no instala en Py3.12) |
| ~~Fase 4 (cuello de botella del controlador)~~ | RESUELTO en corrida 3: ejecutada. Falta solo 4.4 (comparación con otro controlador/`cbench`) |
| Comparación de controladores / `cbench` (Fase 4.4) | Pendiente: `cbench` no está instalado (requiere `apt`, que en `controller` pide contraseña). Se completará con cifras de la literatura, marcadas como tales |
| Emparejamiento exacto sw1↔sw2 y sw1↔sw3 | Sigue pendiente: el bench no reenvía tráfico entre switches, así que el fdb no aprende. Se resolverá con la app de descubrimiento de topología de os-ken (`os_ken.topology`, LLDP por packet-out) conectando los 3 switches, o con un controlador de reenvío real |
| Fase 5 (banco de ataques) | Pendiente: requiere instalar `nmap`/`hping3`/`scapy` en el host atacante (Fase 5.0); los hosts no tienen sudo sin contraseña |
