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
- Commit del repo en el momento de medir: `28c3166` (28c31663c4edd21febefea82c60fbeeda165fb63)

**Alcance de esta corrida: solo fases 1 y 3 (lectura), a pedido explícito.** Las
fases 2, 4 y 5 (que escriben `bench0`, miden Packet-In y lanzan ataques) quedan
pendientes de una sesión aparte.

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

## Fase 2. Capacidad del plano de datos

**No ejecutada en esta corrida** (se pidió empezar solo por fases 1 y 3, de
solo lectura). Pendiente para una sesión que cree y limpie el bridge temporal
`bench0`.

## Fase 4. Cuello de botella del controlador

**No ejecutada.** Además, no se puede ejecutar todavía porque el nodo
`controller` no tiene Ryu instalado (ver hallazgo en Fase 1). Requiere
instalar Ryu primero, con permiso explícito.

## Fase 5. Banco de ataques

**No ejecutada.** Además, tal como está escrito el runbook no se puede
ejecutar sin ajustes: asume `ip netns exec`, que no aplica a este VNRT (ver
hallazgo de Fase 1), y ninguno de los hosts tiene `nmap`/`hping3`/`scapy`
instalado.

## Hallazgos que afectan el diseño

1. **Los tres bridges reales (`sw1`, `sw2`, `sw3`) están configurados solo con
   `protocols=[OpenFlow10]`.** Un controlador OpenFlow 1.3 no puede conectarse
   tal cual están hoy. Bloquea directamente el HLD de R1/R2/R3 y el contrato de
   tablas, que asumen OF1.3. Se necesita `ovs-vsctl set bridge <br>
   protocols=OpenFlow13` en los 3 — cambio de escritura, no aplicado en esta
   corrida, a decidir junto con el ADR 0001.
2. **El diagrama preliminar de topología de `acceso-vnrt.md` estaba
   parcialmente equivocado.** El switch central es `sw1` (conecta a controller,
   sw2 y sw3), no `sw2`. `h2` cuelga de `sw2`, no de `sw1`. Se corrigió la tabla
   de acceso arriba; falta actualizar el diagrama de `acceso-vnrt.md` y el
   futuro documento de arquitectura.
3. **La fase 5 del runbook no es ejecutable tal como está escrita**: no hay
   namespaces (`ip netns`) en este VNRT, cada host es una VM real con su propio
   puerto SSH. Hay que reescribir los comandos de ataque sin `ip netns exec`.
4. **Ningún nodo trae herramientas de prueba/ataque preinstaladas**
   (`nmap`, `hping3`, `scapy`, `cbench`, ni `pip3`). Fases 4 y 5 están
   bloqueadas hasta pedir permiso e instalar lo mínimo necesario.
5. **`controller:ens4` y el puerto interno del bridge `sw1` comparten la misma
   IP (172.16.0.1/24).** No se pudo determinar si es una duplicación real de
   direcciones en el mismo segmento o una convención de direccionamiento
   punto a punto sin impacto — el ping entre ambos siempre se resuelve local
   porque comparten IP, así que no hay forma de probarlo desde dentro de las
   VMs. Consultar con el staff del curso o revisar la plantilla de
   aprovisionamiento del VNRT.
6. **No hay Ryu (ni ningún otro controlador SDN) instalado en `controller`.**
   Bloquea la fase 4 hasta instalarlo con permiso.
7. **No se pudo determinar el emparejamiento exacto sw1–sw2 y sw1–sw3** (qué
   puerto de `sw1` va a cuál). Ver detalle en "Mapa real de topología".

## Pruebas que no se pudieron ejecutar

| Prueba | Motivo |
|---|---|
| `ovs-ofctl -O OpenFlow13 show <br>` en sw1/sw2/sw3 | Los bridges reales solo negocian OpenFlow10; falla la conexión al socket de gestión con "version negotiation failed" |
| `dump-meter-features` / `dump-group-features` en bridges reales | Mismo problema de versión OpenFlow |
| Emparejamiento exacto de puertos sw1↔sw2 y sw1↔sw3 | Sin IP en esos puertos, sin LLDP instalado, sin controlador ni reglas que permitan aislar el tráfico de un enlace específico; el fdb no aprende nada porque `fail_mode=secure` con 0 flujos no reenvía nada |
| LLDP como método de mapeo de adyacencias | `lldpd`/`lldpcli` no están instalados en ningún nodo |
| Versión de Ryu, `pip3 list \| grep ryu` | Ryu y pip3 no están instalados en `controller` |
| `cbench` | No está instalado en ningún nodo |
| Fase 2 completa (capacidad del plano de datos) | No se ejecutó en esta corrida por alcance (solo fases 1 y 3) |
| Fase 4 completa (cuello de botella del controlador) | No se ejecutó por alcance, y además bloqueada porque falta instalar Ryu |
| Fase 5 completa (banco de ataques) | No se ejecutó por alcance, y además bloqueada porque faltan `nmap`/`hping3`/`scapy` y el runbook asume `ip netns exec`, que no aplica aquí |
