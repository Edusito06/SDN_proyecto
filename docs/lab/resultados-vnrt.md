# Resultados del reconocimiento del VNRT

Plantilla que se llena ejecutando `00-reconocimiento-vnrt.md`. Cada dato lleva el
comando que lo produjo. Si algo no se pudo medir, se escribe el motivo, nunca un
número estimado.

- Fecha de ejecución:
- Ejecutado por:
- Método de acceso al entorno:
- Commit del repo en el momento de medir:

## Fase 1. Inventario

### Máquina

| Dato | Valor |
|---|---|
| Kernel y distribución | |
| CPU, modelo y núcleos | |
| RAM | |
| Disco disponible | |

### Open vSwitch

| Dato | Valor |
|---|---|
| Versión de OVS | |
| Versión de ovs-ofctl | |
| Bridges existentes | |
| Datapath type | |
| Protocolos negociados | |
| Fail mode | |
| Número de tablas por bridge | |
| Reglas ya instaladas | |

### Controladores presentes

| Controlador | Instalado | Versión |
|---|---|---|
| Ryu | | |
| ONOS | | |
| OpenDaylight | | |
| Faucet | | |
| Otros | | |

### Herramientas

| Herramienta | Disponible | Versión |
|---|---|---|
| nmap | | |
| hping3 | | |
| iperf3 | | |
| tcpdump | | |
| scapy | | |
| cbench | | |

### Topología existente

Namespaces, interfaces y direccionamiento encontrados:

## Fase 2. Capacidad del plano de datos

### Versiones de OpenFlow soportadas

| Versión | Soportada |
|---|---|
| OpenFlow 1.0 | |
| OpenFlow 1.3 | |
| OpenFlow 1.4 | |
| OpenFlow 1.5 | |

### Funciones que necesita el diseño

| Función | Soportada | Impacto si no lo está |
|---|---|---|
| Múltiples tablas y `goto_table` | | El pipeline del contrato no es implementable |
| `write_metadata` | | R1 no puede pasar el rol a R2 por metadata |
| Meters | | La escalera de mitigación de R3 necesita QoS en su lugar |
| Grupos | | Sin failover ni balanceo por grupos |

### Escala de la tabla de flujos

| N reglas | Instaladas | Tiempo total | Tiempo por regla |
|---|---|---|---|
| 100 | | | |
| 1 000 | | | |
| 5 000 | | | |
| 20 000 | | | |
| 50 000 | | | |

Punto donde empieza a degradarse:

Máximo de reglas aceptado antes de error:

### Latencia según tamaño de tabla

| Reglas en tabla | RTT mediana | RTT p95 |
|---|---|---|
| 0 | | |
| 5 000 | | |
| 50 000 | | |

Observación sobre la caché de megaflows:

## Fase 3. Viabilidad de P4

| Componente | Presente |
|---|---|
| bmv2 / simple_switch | |
| p4c | |
| p4runtime-shell | |
| Modelo o hardware Tofino | |

**Conclusión para el ADR 0001:**

## Fase 4. Cuello de botella del controlador

| Métrica | Valor medido | Compromiso del AVZ02 | Margen |
|---|---|---|---|
| Packet-In por segundo sostenidos | | | |
| Latencia Packet-In a FLOW_MOD, mediana | | | |
| Latencia Packet-In a FLOW_MOD, p95 | | ≤ 500 ms | |
| CPU del controlador bajo 100 flujos/s | | ≤ 60% | |
| CPU del controlador en saturación | | | |

Punto de saturación observado:

Comparación con otra alternativa (indicar si es medida aquí o tomada de la
literatura, con la cita):

## Fase 5. Banco de ataques

| Ataque | Comando | Eventos generados | Duración | Firma observable | ¿Separable del tráfico legítimo? |
|---|---|---|---|---|---|
| Network scanning | | | | | |
| Port scanning rápido | | | | | |
| Port scanning lento (-T1) | | | | | |
| IP spoofing | | | | | |
| Muchos a uno | | | | | |
| Tráfico legítimo intenso | | | | | |

Umbrales propuestos a partir de lo observado, para el HLD de R3:

| Parámetro | Valor propuesto | Justificación desde los datos |
|---|---|---|
| Ventana de observación T | | |
| Umbral de destinos distintos N_dst | | |
| Umbral de puertos distintos N_port | | |
| Umbral de Packet-In fallidos N_miss | | |

## Hallazgos que afectan el diseño

Lista de cosas medidas que obligan a cambiar algo de la arquitectura, el contrato
de tablas o el HLD. Cada una con el ADR o issue que abre.

## Pruebas que no se pudieron ejecutar

| Prueba | Motivo |
|---|---|
| | |
