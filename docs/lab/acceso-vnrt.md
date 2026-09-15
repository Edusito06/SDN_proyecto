# Acceso al VNRT y mapa de la topología

## Cómo se entra

El acceso a cada nodo es por SSH contra un gateway común que hace reenvío de
puertos: un puerto distinto por nodo. Usuario `ubuntu`.

```bash
ssh ubuntu@<GATEWAY> -p <PUERTO>
```

**El `<GATEWAY>` cambia entre sesiones del VNRT.** En la última sesión fue
`10.20.12.153` (antes, en el AVZ02, era `10.20.11.184`). Confirma la IP vigente
antes de empezar y anótala en `resultados-vnrt.md`. Los puertos sí son fijos.

| Nodo | Puerto | Comando |
|---|---|---|
| controller | 5800 | `ssh ubuntu@<GATEWAY> -p 5800` |
| sw1 | 5801 | `ssh ubuntu@<GATEWAY> -p 5801` |
| sw2 | 5802 | `ssh ubuntu@<GATEWAY> -p 5802` |
| sw3 | 5803 | `ssh ubuntu@<GATEWAY> -p 5803` |
| h1 | 5811 | `ssh ubuntu@<GATEWAY> -p 5811` |
| h2 | 5812 | `ssh ubuntu@<GATEWAY> -p 5812` |
| h3 | 5813 | `ssh ubuntu@<GATEWAY> -p 5813` |
| h4 | 5814 | `ssh ubuntu@<GATEWAY> -p 5814` |

Regla mnemotécnica: 580x son los del plano de red (controlador y switches),
581x son los hosts, en orden h1 a h4.

Hay un helper en `scripts/vnrt-ssh.sh` que envuelve esto. Uso:

```bash
export VNRT_GW=10.20.12.153            # la IP de hoy
scripts/vnrt-ssh.sh sw1 'ovs-vsctl show'   # corre un comando en sw1 y vuelve
scripts/vnrt-ssh.sh h2                       # abre sesión interactiva en h2
```

## Nodos del entorno

- **controller**: donde corre el controlador SDN (Ryu). Es el nodo desde el que
  se lanza `ryu-manager` y donde vive la lógica de R1, R2 y R3.
- **sw1, sw2, sw3**: los switches Open vSwitch del plano de datos.
- **h1, h2, h3, h4**: hosts de usuario. Uno de ellos hará de atacante en las
  pruebas de R3.
- **gateway**: salida hacia el exterior. Relevante para R5 (perímetro), que no es
  de este grupo, pero conviene tenerlo mapeado para el análisis cualitativo.
- **MP_Link 0**: red de gestión (las líneas verdes del diagrama). Conecta a todos
  los nodos por administración. **No es el plano de datos** y no debe confundirse
  con los enlaces de tráfico real (líneas azules).

## Topología según el diagrama

Interpretación a partir de la imagen del VNRT. Las líneas verdes son gestión
(MP_Link) y las azules son enlaces de datos.

**Lectura preliminar de la imagen (ya verificada y corregida, ver abajo):**

- ~~sw1 conecta con: h2, controller, y sube hacia sw2.~~
- ~~sw2 conecta con: h1, y enlaza con sw1 y sw3. Parece el switch central.~~
- ~~sw3 conecta con: h3, h4, y baja hacia sw2.~~
- ~~Cadena `sw1 — sw2 — sw3` con hosts colgando de cada switch.~~

## Topología real, verificada en la fase 1 del reconocimiento (2026-09-15)

Confirmada por correlación de contadores de tráfico (`ip -s link show`, sin
tocar ninguna configuración de OVS) contra los 3 switches reales. Detalle
completo del método y los números en `resultados-vnrt.md`.

- **sw1** es el switch central: conecta al **controller** (`sw1/ens4`) y sube a
  **sw2** y **sw3** por sus otros dos puertos de datos (`ens5`, `ens6` — no se
  pudo determinar cuál va a cuál, ver pendientes en `resultados-vnrt.md`).
- **sw2** conecta con **h1** (`ens5`) y **h2** (`ens6`), no con h2 solamente
  como decía la lectura preliminar.
- **sw3** conecta con **h3** (`ens5`) y **h4** (`ens6`), como se asumía.

Es decir, topología en estrella con `sw1` en el centro (controller + sw2 + sw3),
y los cuatro hosts repartidos dos y dos entre `sw2` y `sw3`. **No** es la cadena
`sw1 — sw2 — sw3` que asumía la lectura preliminar del diagrama.

## Qué debe verificar Claude Code sobre la topología

En cada switch, con OVS, sacar el mapeo real de puertos y vecinos:

```bash
# En cada swN
ovs-vsctl show
ovs-ofctl -O OpenFlow13 show <bridge>          # puertos y su numeración OpenFlow
ovs-appctl fdb/show <bridge>                    # MACs aprendidas por puerto
```

Y si hay LLDP activo, usarlo para el mapa de adyacencias. Con eso se construye la
tabla real de "puerto X de swN va a nodo Y", que es la que se necesita para:

- El diagrama de topología del documento de arquitectura (la rúbrica pide
  topología clara).
- Saber en qué switch y puerto entra cada host, dato imprescindible para la
  detección de IP spoofing de R3, que compara IP, MAC y puerto de ingreso.
- Ubicar dónde conviene poner el enforcement de R2 y la detección de R3.

## Notas de seguridad para las pruebas

Los hosts h1 a h4 y los switches son del laboratorio. Los ataques de la fase 5
del reconocimiento se lanzan desde un host hacia otro host o servidor **del
propio VNRT**. El gateway da salida al exterior: no se lanza tráfico de ataque
hacia afuera a través de él bajo ninguna circunstancia.
