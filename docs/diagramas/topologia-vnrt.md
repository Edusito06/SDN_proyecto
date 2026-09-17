# Topología del VNRT — verificada experimentalmente

Todos los datos de este documento salen de la medición directa sobre el entorno
(fases 1 y 4 del reconocimiento, ver `../lab/resultados-vnrt.md`), no del diagrama
que entrega la plataforma. El diagrama original resultó estar parcialmente
equivocado: asumía una cadena `sw1—sw2—sw3` con `sw2` central y `h2` colgando de
`sw1`. Lo real es una **estrella con `sw1` en el centro**.

## Plano de datos (lo que controla OpenFlow)

```
                        ┌───────────────────────┐
                        │  Controlador os-ken   │
                        │  192.168.0.10:6653    │
                        │  2 vCPU / 1.9 GiB     │
                        └───────────┬───────────┘
                                    │  canal OpenFlow
                                    │  (por la red de GESTIÓN)
                        ┌───────────┴───────────┐
                        │        sw1            │   dpid 0000a223f2c04547
                        │   SWITCH CENTRAL      │   OF puerto 1 = ens4 -> controlador
                        │   OVS 3.3.9 / OF1.3   │   OF puertos 2,3 = enlaces a sw2/sw3
                        └─────┬───────────┬─────┘   (emparejamiento exacto pendiente)
                              │           │
                  ┌───────────┘           └───────────┐
                  │                                   │
        ┌─────────┴─────────┐               ┌─────────┴─────────┐
        │       sw2         │               │       sw3         │
        │ dpid ...9039894a  │               │ dpid ...2d265744  │
        │ OF1 = ens4 (up)   │               │ OF3 = ens4 (up)   │
        └──┬─────────────┬──┘               └──┬─────────────┬──┘
     OF2/ens5         OF3/ens6            OF2/ens5        OF1/ens6
           │             │                     │             │
      ┌────┴───┐    ┌────┴───┐            ┌────┴────┐   ┌────┴─────┐
      │   h1   │    │   h2   │            │   h3    │   │    h4    │
      │10.0.0.1│    │10.0.0.2│            │10.0.0.3 │   │ 10.0.0.4 │
      │CLIENTE │    │CLIENTE │            │ NOTAS   │   │  REPO    │
      │        │    │        │            │ (crít.) │   │ EXÁMENES │
      └────────┘    └────────┘            └─────────┘   │ (crítico)│
                                                        └──────────┘
        ── clientes (sw2) ──              ── recursos protegidos (sw3) ──

  Todo acceso cliente -> recurso privilegiado CRUZA sw1.
```

## Las tres redes y para qué sirve cada una

Distinción crítica, porque los avances entregados la tenían cambiada:

| Red | Función real | Interfaz | Quién la usa |
|---|---|---|---|
| `10.0.0.0/24` | **Plano de datos.** Tráfico de usuario. Es lo que R1, R2 y R3 controlan | `ens4` de h1-h4 | Hosts |
| `192.168.0.0/24` | **Gestión.** Canal OpenFlow switch↔controlador, y acceso SSH | `ens3` de todos | Controlador y switches |
| `172.16.0.0/24` | Direcciones internas de los bridges OVS. **No se usa** para el canal de control | puerto interno del bridge | — |

## Tabla de acceso: qué host entra por qué puerto

Dato imprescindible para la detección de IP spoofing de R3, que compara la terna
(IP, MAC, puerto de ingreso). Verificado por correlación de contadores de tráfico.

| Nodo | IP de datos | MAC (`ens4`) | Switch | Puerto OF | Papel en R2 |
|---|---|---|---|---|---|
| controller | — | `fa:16:3e:77:ae:92` | sw1 | 1 | plano de control |
| h1 | 10.0.0.1 | `fa:16:3e:9f:b2:02` | sw2 | 2 | cliente |
| h2 | 10.0.0.2 | `fa:16:3e:bb:e9:aa` | sw2 | 3 | cliente |
| h3 | 10.0.0.3 | `fa:16:3e:ef:46:b7` | sw3 | 2 | **servidor de notas** |
| h4 | 10.0.0.4 | `fa:16:3e:35:f5:89` | sw3 | 1 | **repositorio de exámenes** |

Ojo al escribir reglas: en `sw3` la numeración OpenFlow **no** sigue el orden de
`ensN` (OF 1 = ens6, OF 3 = ens4). Usar siempre el número OpenFlow.

## Pipeline de tablas sobre esta topología

```
  paquete de h2 (alumno) hacia 10.0.0.3 (notas)
        │
        ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ tabla 0  │──▶│ tabla 1  │──▶│ tabla 2  │──▶│ tabla 3  │──▶│ tabla 4  │
   │   R3     │   │   R3     │   │   R1     │   │   R2     │   │  común   │
   │anti-spoof│   │mitigación│   │ identidad│   │ política │   │ reenvío  │
   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
   IP+MAC+puerto  ¿es atacante   escribe rol     lee rol en     salida por
   ¿coinciden?    confirmado?    en metadata     metadata       el puerto
        │              │              │               │
     descarta       descarta      Packet-In      DROP: alumno
     spoofing       atacante      si no conoce   no accede a notas
```

## Estado del entorno tras el reconocimiento

| Elemento | Estado | Nota |
|---|---|---|
| OpenFlow | **1.3 habilitado** en sw1, sw2, sw3 | Venían en 1.0; se corrigió en el Paso 0 |
| Tablas por bridge | 254 | El pipeline de 5 tablas cabe de sobra |
| `fail_mode` | `secure` | Sin controlador, el switch no reenvía nada |
| Flujos instalados | 0 | Entorno limpio, listo para los módulos |
| Controlador | os-ken 4.2.2 en venv | Ryu no instala en Python 3.12 |
| Meters | **Soportados** | Habilitan la escalera de mitigación de R3 |
