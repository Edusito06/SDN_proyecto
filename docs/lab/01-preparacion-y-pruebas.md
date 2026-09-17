# Preparación del entorno y ejecución de las fases 2, 4 y 5

Runbook de continuación. Se ejecuta después de `00-reconocimiento-vnrt.md`, que
ya dejó el inventario en `resultados-vnrt.md`. Corrige los supuestos que aquel
tenía mal y ordena el trabajo que sí escribe en el entorno.

## Autorizaciones vigentes

Eduardo autorizó (15/09/2026) instalar lo mínimo necesario en el VNRT para
completar las fases pendientes. Aun así:

- Instala solo lo que aparece en este documento. Nada más.
- Antes de instalar en un nodo, deja registrado en `resultados-vnrt.md` qué vas a
  instalar y con qué comando.
- Si un `apt install` falla por falta de red o de repositorios, regístralo y
  detente en esa fase; no busques atajos ni compiles desde fuente.
- Recordatorio para el grupo: conviene avisar al coach que el entorno se va a
  modificar, por si el VNRT se reaprovisiona y se pierde lo instalado.

## Correcciones al runbook anterior

El runbook `00-reconocimiento-vnrt.md` fue escrito antes de conocer el entorno y
tenía dos supuestos equivocados que este documento reemplaza:

1. **Los hosts NO son namespaces.** `h1` a `h4` son VMs independientes, cada una
   con su propio puerto SSH. Todos los comandos que en el runbook viejo llevaban
   `ip netns exec <host> ...` se ejecutan aquí **directamente en la shell del
   host**, entrando por su SSH. Olvida `ip netns` en este VNRT.
2. **Los bridges reales venían configurados solo con OpenFlow 1.0** (no por
   falta de soporte del software: OVS 3.3.9 soporta 1.0 a 1.5, confirmado en la
   fase 2 sobre `bench0`; era la configuración por bridge la que estaba en 1.0).
   Hubo que habilitar 1.3 antes de conectar el controlador (paso 0 de abajo).

## Paso 0: habilitar OpenFlow 1.3 en los tres switches

> **Estado: ya ejecutado** (corrida 2, 2026-09-15). Los tres switches quedaron
> en `protocols=[OpenFlow13]` y el resultado está documentado en
> `resultados-vnrt.md`, sección "Paso 0". El VNRT **sí soporta OpenFlow 1.3**;
> lo que faltaba era prenderlo por bridge, no instalar ni compilar nada. Esta
> sección queda como referencia de cómo se hizo y de cómo repetirlo si el VNRT
> se reaprovisiona y los bridges vuelven a su configuración por defecto.

Sin esto, un controlador que hable OF1.3 no completa el handshake. En cada
switch (`sw1`, `sw2`, `sw3`), por SSH:

```bash
sudo ovs-vsctl set bridge <nombre_bridge> protocols=OpenFlow13
sudo ovs-vsctl get bridge <nombre_bridge> protocols   # confirmar [OpenFlow13]
sudo ovs-ofctl -O OpenFlow13 show <nombre_bridge>      # ahora debe responder
```

El nombre del bridge es igual al hostname (`sw1`, `sw2`, `sw3`). Registra en
`resultados-vnrt.md` que el cambio quedó aplicado y que `dump-flows` sigue en 0.

## Fase 2: capacidad del plano de datos

Sobre un bridge temporal `bench0`, aislado de la topología real. Elige uno de los
switches para crearlo (por ejemplo `sw1`). Sigue la fase 2 de
`00-reconocimiento-vnrt.md` tal como está (esa parte sí era correcta):

- Crear `bench0` con `protocols=OpenFlow13`.
- Probar qué versiones de OpenFlow negocia.
- Probar `write_metadata`, `goto_table`, meters y grupos. **El resultado de
  meters es crítico**: si no están soportados, la escalera de mitigación de R3
  cambia. Anótalo destacado.
- Medir instalación de reglas a N = 100, 1000, 5000, 20000, 50000 y ver dónde se
  degrada.
- **Limpiar**: `del-flows bench0` y `del-br bench0`. Confirmar que `bench0` ya no
  aparece en `ovs-vsctl show`.

Vuelca todo en la sección Fase 2 de `resultados-vnrt.md`.

## Fase 4: instalar Ryu y medir el controlador

### 4.0 Instalar Ryu en el nodo `controller`

Ryu depende de una versión de Python y de librerías (`eventlet`, `webob`) que en
Ubuntu 24.04 suelen dar conflicto si se instala a lo bruto. Usa un entorno
virtual, no toques el Python del sistema:

```bash
# en controller
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
python3 -m venv ~/ryu-venv
source ~/ryu-venv/bin/activate
pip install --upgrade pip
pip install ryu
ryu-manager --version
```

Si `pip install ryu` falla por incompatibilidades de `eventlet` con Python 3.12
(es un problema conocido), registra el error exacto y prueba la variante
mantenida `os-ken` (el fork de Ryu que sigue vivo):

```bash
pip install os-ken
os-ken-manager --version
```

Anota en `resultados-vnrt.md` cuál de los dos quedó funcionando y con qué
versión. Con cualquiera de los dos el resto del proyecto es equivalente; si
resulta ser `os-ken`, déjalo dicho porque afecta los imports del código.

### 4.1 App de medición

Escribe `tools/bench_packetin.py`: aplicación mínima que por cada
`EventOFPPacketIn` incremente un contador, registre el timestamp, y cada segundo
imprima Packet-In por segundo. Que además mida el tiempo entre recibir el
Packet-In y confirmar el FLOW_MOD. No instala reglas de reenvío reales.

Levanta el controlador y conéctale un switch de prueba (puede ser `bench0` con su
`set-controller` apuntando al controller, o uno de los switches reales ya en
OF1.3). Registra el `dpid` que se conecta.

### 4.2 Generar carga desde un host

Cada destino nuevo produce un table-miss y por lo tanto un Packet-In. **Sin `ip
netns`**, directo en el host (por ejemplo `h1`), sobre su interfaz de datos
`ens4`:

```bash
# en h1, con scapy ya instalado (ver Fase 5 para la instalacion)
sudo python3 -c "
from scapy.all import *
import time
for i in range(2000):
    sendp(Ether()/IP(dst='10.0.%d.%d' % (i//256, i%256))/ICMP(), iface='ens4', verbose=0)
    time.sleep(0.002)
"
```

### 4.3 Qué anotar

Packet-In por segundo sostenidos antes de que la latencia se dispare, latencia
mediana y p95 de Packet-In a FLOW_MOD, y CPU del proceso del controlador en ese
punto (recuerda: el controller tiene 2 vCPU). Compara contra el compromiso del
AVZ02: detección en 500 ms y CPU bajo 60% con 100 flujos/s. Este número es el
techo de toda la solución de R3.

## Fase 5: banco de ataques para R3

### 5.0 Instalar herramientas en el host atacante

Elige un host como atacante. Por la topología, **`h3` o `h4` (ambos en sw3)**
son buenos atacantes contra un objetivo en sw2 (`h1` o `h2`), porque el tráfico
cruza el enlace entre switches y pasa por sw1, que es donde conviene detectar.

```bash
# en el host atacante, por ejemplo h4
sudo apt-get update
sudo apt-get install -y nmap hping3 python3-scapy
nmap --version; hping3 --version
```

En el host objetivo, para medir tráfico legítimo (falsos positivos), instala
`iperf3`:

```bash
# en el host objetivo, por ejemplo h1
sudo apt-get install -y iperf3
```

### 5.1 Escenarios

Todo **dentro del VNRT**, de un host a otro. Nunca hacia el gateway ni fuera del
entorno. Sin `ip netns`, directo en la shell del host atacante:

```bash
# Network scanning: hosts vivos en el segmento de datos
sudo nmap -sn 10.0.0.0/24

# Port scanning contra el objetivo
sudo nmap -sS -p 1-1000 10.0.0.1

# Scan lento, el caso dificil: debe detectarse igual
sudo nmap -sS -T1 -p 1-100 10.0.0.1

# IP spoofing: origen falsificado
sudo hping3 -a 10.0.0.99 -S -p 80 -c 100 10.0.0.1

# Muchos a uno / saturacion
sudo hping3 --flood -S -p 80 10.0.0.1

# Trafico legitimo intenso, para medir falsos positivos (objetivo corre: iperf3 -s)
iperf3 -c 10.0.0.1 -t 30
```

### 5.2 Qué anotar

Para cada ataque: firma observable en los Packet-In que llegan al controlador,
cuántos eventos genera y en cuánto tiempo, y si un umbral razonable lo separa del
tráfico legítimo del `iperf3`. El scan lento con `-T1` es el que decide si el
diseño de detección sirve, porque es el que más se parece al tráfico normal. Con
estos datos se llenan los umbrales T, N_dst, N_port y N_miss del HLD de R3.

## Cierre

Cuando termines, completa las secciones correspondientes de `resultados-vnrt.md`,
resuelve el pendiente del emparejamiento sw1 a sw2 y sw1 a sw3 (ahora que hay un
controlador conectado y reglas, el fdb sí aprende y se puede mapear), y abre un
Pull Request desde `feature/reconocimiento-vnrt`. Si la fase 2 revela que no hay
meters, abre un ADR nuevo para el rediseño de la mitigación de R3 en vez de
editar el contrato de tablas por tu cuenta.
