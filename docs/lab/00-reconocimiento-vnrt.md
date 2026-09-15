# Runbook: reconocimiento y caracterización del entorno VNRT

Documento operativo para Claude Code. Léelo completo antes de ejecutar nada.

## Por qué existe este documento

El ADR 0001 (`docs/adr/0001-controlador-y-plano-de-datos.md`) está pendiente: hay
que decidir entre Ryu sobre Open vSwitch y un plano de datos programable con P4.
Esa decisión no se puede tomar por preferencia, porque la rúbrica del Ex1 evalúa
"elección de controlador fundamentada" y el jurado va a preguntar por qué.

Este runbook levanta los datos que faltan para cerrarla: qué hay realmente
instalado en el VNRT, qué versiones de OpenFlow soporta, si existe algún camino
viable a P4, y cuánto aguanta el controlador antes de degradarse.

## Advertencia conceptual, léela antes de medir

**El VNRT es un entorno virtualizado. Open vSwitch es un switch por software
corriendo sobre x86, no tiene TCAM.** Lo que OVS tiene es una tabla de flujos en
memoria de usuario más una caché de megaflows en el kernel. Por eso:

- Las mediciones de este runbook dicen cuántas reglas aguanta OVS y a qué
  velocidad, no cuántas entradas de TCAM consumiría un switch físico.
- La estimación de TCAM que pide la rúbrica de R2 con peso 10 **sigue siendo un
  cálculo analítico** sobre un modelo de switch de hardware. No la reemplaces con
  un número medido en OVS: sería un error conceptual y el jurado lo puede notar.
- Lo correcto es presentar las dos cosas por separado: el presupuesto de TCAM
  calculado para hardware, y el comportamiento medido del prototipo en OVS.

Lo mismo aplica a la elección de controlador. El VNRT no te va a decir qué
controlador es mejor en abstracto. Te va a decir **qué es posible aquí** y
**dónde está el cuello de botella**, que es exactamente lo que necesitas para
justificar la decisión con datos y no con opinión.

## Reglas de trabajo

1. Las fases 1 y 3 son de **solo lectura**. No modifican nada.
2. La fase 2 y la 4 crean recursos temporales con el prefijo `bench`. Todo se
   borra al final de cada fase. Nunca toques los bridges de la topología del
   grupo.
3. Antes de cualquier fase que escriba, respalda el estado:
   `ovs-vsctl show > /tmp/ovs-antes.txt` y `ovs-ofctl -O OpenFlow13 dump-flows <br> > /tmp/flows-antes.txt`.
4. Los ataques de la fase 5 se ejecutan **solo dentro de la topología del
   laboratorio**, contra hosts virtuales del propio entorno. Nunca contra la red
   de la universidad ni contra ninguna IP fuera del VNRT.
5. Los resultados se escriben en `docs/lab/resultados-vnrt.md`, no en el chat.
   Cada dato con el comando que lo produjo, para que sea reproducible.
6. Si un comando falla, registra el error tal cual en el archivo de resultados y
   sigue con la siguiente prueba. No improvises instalaciones ni cambies la
   configuración del entorno para que una prueba pase.
7. No instales paquetes sin preguntar. El entorno es compartido con el curso.

## Paso 0: acceso al entorno

El detalle completo de acceso y el mapa de la topología están en
`docs/lab/acceso-vnrt.md`. Léelo antes de seguir. En resumen:

Cada nodo se alcanza por SSH contra un gateway común con reenvío de puertos,
usuario `ubuntu`, un puerto por nodo:

| Nodo | Puerto | | Nodo | Puerto |
|---|---|---|---|---|
| controller | 5800 | | h1 | 5811 |
| sw1 | 5801 | | h2 | 5812 |
| sw2 | 5802 | | h3 | 5813 |
| sw3 | 5803 | | h4 | 5814 |

```bash
ssh ubuntu@<GATEWAY> -p 5801   # ejemplo: sw1
```

**El `<GATEWAY>` cambia entre sesiones del VNRT.** Pídele a Eduardo la IP vigente,
confírmala y anótala como primera línea de `resultados-vnrt.md`. Los puertos son
fijos. Hay un helper en `scripts/vnrt-ssh.sh` que evita memorizar puertos.

Importante: **cada nodo es una máquina distinta**. El reconocimiento se hace nodo
por nodo. Los comandos de OVS de la fase 1.2 y 2 corren dentro de sw1, sw2 y sw3;
los de controladores y la app de medición corren dentro de `controller`; los
ataques de la fase 5 se lanzan desde el host que haga de atacante. No asumas que
todo vive en una sola shell.

Antes de nada, en cada nodo al que entres, verifica y anota qué es:

```bash
hostname; whoami; id
ip -br a
```

Primera tarea concreta de la fase 1: recorrer los ocho nodos, confirmar el mapa
de topología preliminar de `acceso-vnrt.md` contra lo que reportan los switches
(puertos OpenFlow, MACs aprendidas, LLDP si lo hay) y dejar en `resultados-vnrt.md`
la tabla real de qué puerto de cada switch va a qué nodo. Ese mapa es
imprescindible para la detección de IP spoofing de R3.

## Fase 1: inventario del entorno (solo lectura)

### 1.1 Máquina

```bash
uname -a
cat /etc/os-release | head -3
nproc
grep -m1 "model name" /proc/cpuinfo
free -h
df -h /
```

### 1.2 Open vSwitch

```bash
ovs-vsctl --version
ovs-ofctl --version
ovs-vsctl show

for br in $(ovs-vsctl list-br); do
  echo "=== $br"
  ovs-vsctl get bridge "$br" datapath_type protocols fail_mode
  ovs-ofctl -O OpenFlow13 show "$br" | head -20
  echo "reglas actuales: $(ovs-ofctl -O OpenFlow13 dump-flows "$br" | wc -l)"
done

ovs-appctl dpif/show
ovs-dpctl show
```

Lo que importa anotar: versión de OVS, versiones de OpenFlow negociadas
(`protocols`), tipo de datapath (`system` significa kernel, `netdev` significa
espacio de usuario o DPDK), número de tablas que reporta cada bridge, y cuántos
puertos tiene cada uno.

### 1.3 Controladores disponibles

```bash
command -v ryu-manager && ryu-manager --version
python3 --version
pip3 list 2>/dev/null | grep -iE 'ryu|eventlet|webob|oslo|routes'
for c in onos karaf opendaylight faucet gauge pox nox; do
  printf "%-14s %s\n" "$c" "$(command -v $c || echo NO)"
done
ls /opt 2>/dev/null
```

### 1.4 Herramientas de prueba

```bash
for t in nmap hping3 iperf3 iperf tcpdump tshark mausezahn ping arping \
         curl jq bc python3 pip3 git tmux; do
  printf "%-12s %s\n" "$t" "$(command -v $t || echo NO)"
done
python3 -c "import scapy; print('scapy', scapy.__version__)" 2>/dev/null || echo "scapy NO"
command -v cbench && echo "cbench disponible"
```

### 1.5 Topología existente

```bash
ip netns list
for ns in $(ip netns list | awk '{print $1}'); do
  echo "=== $ns"; ip netns exec "$ns" ip -br a
done
ip -br link | grep -E 'veth|ovs'
```

## Fase 2: capacidad del plano de datos

Todo esto ocurre sobre un bridge temporal `bench0`, aislado de la topología real.

```bash
ovs-vsctl add-br bench0 -- set bridge bench0 protocols=OpenFlow13
ovs-vsctl get bridge bench0 protocols
```

### 2.1 Versiones de OpenFlow realmente soportadas

```bash
for v in OpenFlow10 OpenFlow11 OpenFlow12 OpenFlow13 OpenFlow14 OpenFlow15; do
  if ovs-ofctl -O $v show bench0 >/dev/null 2>&1; then echo "$v SI"; else echo "$v no"; fi
done
```

Esto decide si el pipeline multitabla de `docs/contratos/tablas-openflow.md` es
implementable tal cual. Necesita 1.3 o superior. Si solo hubiera 1.0, no hay
múltiples tablas ni `metadata` y habría que rediseñar el contrato.

### 2.2 Soporte de las funciones que necesita el diseño

```bash
# metadata y goto_table, que usa el contrato de tablas
ovs-ofctl -O OpenFlow13 add-flow bench0 \
  "table=0,priority=100,ip,actions=write_metadata:0x1/0xf,goto_table:1" && echo "metadata+goto_table OK"

# meters, que necesita la escalera de mitigación de R3 (rate limit)
ovs-ofctl -O OpenFlow13 dump-meter-features bench0
ovs-ofctl -O OpenFlow13 add-meter bench0 "meter=1,kbps,band=type=drop,rate=1000" \
  && echo "meters OK" || echo "meters NO SOPORTADOS"

# grupos, por si se usa para failover o balanceo
ovs-ofctl -O OpenFlow13 dump-group-features bench0
```

Si los meters no están soportados, el nivel 1 de la escalera de mitigación de R3
tiene que rediseñarse con colas de QoS en vez de meters. Es un hallazgo
importante, anótalo destacado.

### 2.3 Escala y velocidad de instalación de reglas

```bash
for N in 100 1000 5000 20000 50000; do
  python3 -c "
for i in range($N):
    print('priority=100,ip,nw_src=10.%d.%d.%d,actions=drop' % (i//65536%256, i//256%256, i%256))
" > /tmp/bench_flows.txt
  ovs-ofctl -O OpenFlow13 del-flows bench0 2>/dev/null
  INICIO=$(date +%s.%N)
  ovs-ofctl -O OpenFlow13 add-flows bench0 /tmp/bench_flows.txt
  FIN=$(date +%s.%N)
  INSTALADAS=$(ovs-ofctl -O OpenFlow13 dump-flows bench0 | grep -c "priority=100")
  echo "N=$N instaladas=$INSTALADAS tiempo=$(echo "$FIN - $INICIO" | bc)s"
done
```

Anota a partir de qué N empieza a degradarse el tiempo por regla, y si en algún
punto OVS rechaza reglas. Esto sustenta el criterio de escalabilidad de la
rúbrica y el argumento de por qué hay que agregar reglas por subred y rol en vez
de por host.

### 2.4 Costo de consulta según el tamaño de la tabla

Con la tabla cargada a distintos N, mide la latencia de ida y vuelta entre dos
hosts de prueba y observa si crece. Dato esperado: **casi no crece**, porque la
caché de megaflows del kernel absorbe el costo. Ese resultado es interesante
justamente porque contrasta con el comportamiento de una TCAM real, y da material
para la sección de análisis cuantitativo.

### 2.5 Limpieza obligatoria

```bash
ovs-ofctl -O OpenFlow13 del-flows bench0
ovs-vsctl del-br bench0
ovs-vsctl show   # confirmar que bench0 ya no aparece
```

## Fase 3: viabilidad real de P4 (solo lectura)

Esta fase responde la pregunta que bloquea el ADR 0001.

```bash
for b in simple_switch simple_switch_grpc simple_switch_CLI p4c p4c-bm2-ss \
         bmv2 psa_switch bf_switchd; do
  printf "%-20s %s\n" "$b" "$(command -v $b || echo NO)"
done
dpkg -l 2>/dev/null | grep -iE ' p4|bmv2|behavioral-model' || echo "sin paquetes p4/bmv2"
ls /usr/local/bin 2>/dev/null | grep -iE 'p4|switch'
python3 -c "import p4runtime_sh" 2>/dev/null && echo "p4runtime-shell OK" || echo "p4runtime-shell NO"
find / -maxdepth 4 -iname '*tofino*' 2>/dev/null | head
```

Regla de decisión, para escribirla directamente en el ADR:

| Hallazgo | Conclusión para el ADR 0001 |
|---|---|
| No hay bmv2 ni p4c ni Tofino | La opción B queda descartada por entorno. Se documenta como alternativa evaluada y no disponible. Va la opción A. |
| Hay bmv2 o p4c pero sin Tofino | La opción C es técnicamente posible pero costosa. Evaluar si entra en el calendario del Ex2, no del Ex1. |
| Hay acceso a Tofino o a su modelo | Recién ahí la opción B merece discutirse en serio, y aun así con el riesgo de calendario del parcial. |

En los tres casos, el resultado es un dato verificable que justifica la decisión
ante el jurado, que es exactamente lo que pide la rúbrica.

## Fase 4: dónde está el cuello de botella del controlador

Este es el dato más valioso del runbook, porque el diseño de R3 depende de él: si
la detección se hace contando Packet-In en el controlador, la capacidad de
Packet-In por segundo es el techo de toda la solución.

### 4.1 Aplicación de medición

Escribe `tools/bench_packetin.py`: una aplicación Ryu mínima que, por cada
`EventOFPPacketIn`, incremente un contador y registre la marca de tiempo, y que
cada segundo imprima la tasa. Que además mida el tiempo entre recibir el
Packet-In y confirmar el FLOW_MOD correspondiente. No instales reglas de
reenvío reales: el objetivo es medir el plano de control, no mover tráfico.

### 4.2 Generación de carga

Desde un namespace del laboratorio, genera flujos nuevos a ritmo creciente. Cada
destino distinto produce un table-miss y por lo tanto un Packet-In:

```bash
ip netns exec h1 python3 -c "
from scapy.all import *
import time
for i in range(2000):
    sendp(Ether()/IP(dst='10.0.%d.%d' % (i//256, i%256))/ICMP(), iface='h1-eth0', verbose=0)
    time.sleep(0.002)
"
```

Si `cbench` está disponible, úsalo también: es el estándar para este tipo de
medición y sus números son más citables.

### 4.3 Qué anotar

Packet-In por segundo sostenidos antes de que la latencia se dispare, latencia
mediana y percentil 95 de Packet-In a FLOW_MOD, y uso de CPU del proceso del
controlador en ese punto. Compara contra los compromisos del AVZ02: detección en
500 ms y CPU por debajo de 60% bajo 100 flujos por segundo. Si el margen resulta
holgado, dilo; si resulta ajustado, es un hallazgo de diseño que hay que llevar
al HLD de R3.

### 4.4 Comparación con al menos otra alternativa

Para que la elección de controlador sea "fundamentada" y no una preferencia, hace
falta un punto de comparación. En orden de esfuerzo: repetir la medición con la
misma app sobre otro controlador si hay alguno instalado, o si no lo hay,
documentar la comparación con datos publicados y citarlos, dejando claro que son
de la literatura y no medidos aquí. Nunca presentes un número de la literatura
como si lo hubieras medido.

## Fase 5: banco de ataques para R3

Solo dentro de la topología del laboratorio.

```bash
# Network scanning: descubrimiento de hosts vivos
ip netns exec atacante nmap -sn 192.168.0.0/24

# Port scanning: SYN scan contra un host del laboratorio
ip netns exec atacante nmap -sS -p 1-1000 192.168.0.10

# Scan lento, el caso difícil: debe detectarse igual
ip netns exec atacante nmap -sS -T1 -p 1-100 192.168.0.10

# IP spoofing
ip netns exec atacante hping3 -a 192.168.0.99 -S -p 80 -c 100 192.168.0.10

# Muchos a uno
ip netns exec atacante hping3 --flood -S -p 80 192.168.0.10

# Tráfico legítimo intenso, para medir falsos positivos
ip netns exec h2 iperf3 -c 192.168.0.10 -t 30
```

Para cada uno anota: firma observable en los Packet-In, cuántos eventos genera y
en cuánto tiempo, y si un umbral razonable lo separa del tráfico legítimo. El
escaneo lento con `-T1` es el que define si el diseño de detección sirve o no,
porque es el que se parece al tráfico normal.

## Fase 6: cerrar el ADR

Cuando termines las cinco fases:

1. Completa `docs/lab/resultados-vnrt.md` con todo lo medido.
2. Actualiza `docs/adr/0001-controlador-y-plano-de-datos.md`: cambia el estado de
   PENDIENTE a la decisión tomada, apoya cada argumento en un dato de la fase
   correspondiente y completa la sección de consecuencias.
3. Si algún hallazgo invalida el contrato de tablas (por ejemplo, que no haya
   meters, o que no haya OpenFlow 1.3), abre un ADR nuevo en vez de editar el
   contrato por tu cuenta. El contrato lo aprueba el arquitecto de solución.
4. Haz commit en una rama `feature/reconocimiento-vnrt` y abre Pull Request.

## Lo que no debes hacer

No cambies la configuración del entorno compartido para que una medición salga
mejor. No borres ni modifiques bridges, flujos o namespaces que no hayas creado
tú. No tomes la decisión del ADR por tu cuenta: tu trabajo es dejar la evidencia
ordenada y la recomendación escrita; la decisión la firma Eduardo como arquitecto
de solución, porque es quien la va a defender oralmente. Y no inventes ningún
número: si una prueba no se pudo correr, se escribe "no se pudo medir" y el
motivo.
