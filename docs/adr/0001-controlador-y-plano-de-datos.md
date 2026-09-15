# ADR 0001 — Controlador y plano de datos

- Estado: **ACEPTADO**
- Fecha: 2026-09-15
- Decide: Eduardo Rodas (arquitecto), pendiente de comentar en la asesoría del coach
- Sustento: reconocimiento del VNRT, fases 1 y 3 (`docs/lab/resultados-vnrt.md`)

## Contexto

Había una inconsistencia entre los avances entregados. El AVZ01 planteaba
implementar R3 con P4 sobre Intel Tofino. El AVZ02 y el AVZ03 describían
controlador Ryu sobre Open vSwitch con OpenFlow. Son dos arquitecturas distintas,
y la rúbrica del Ex1 evalúa "elección de controlador fundamentada" con peso 8,
así que la decisión no podía quedar ambigua.

Para no decidir por preferencia, se ejecutó un reconocimiento del entorno VNRT
(runbook `docs/lab/00-reconocimiento-vnrt.md`). Los datos relevantes:

- No existe ningún componente de la cadena P4 en ninguno de los 8 nodos: ni
  compilador `p4c`, ni switch de software `bmv2`/`simple_switch`, ni
  `p4runtime-shell`, ni rastro de hardware o modelo Tofino
  (`find / -iname '*tofino*'` vacío en los 8 nodos).
- El plano de datos ya está montado sobre Open vSwitch 3.3.9 en los tres
  switches, con la topología en estrella `sw1` central descrita en los
  resultados.
- Los bridges soportan OpenFlow 1.3 y superiores a nivel de binario; hoy están
  configurados en OpenFlow 1.0, lo que se corrige con una línea de `ovs-vsctl`.

## Decisión

**Se adopta Ryu sobre Open vSwitch con OpenFlow 1.3 para toda la solución (R1, R2
y R3) del Ex1.** La vía P4/Tofino queda descartada por no estar disponible en el
entorno, y se documenta como alternativa evaluada.

## Justificación

Es una decisión forzada por los datos, no por gusto. La opción P4/Tofino (opción
B del planteamiento original) es inviable en el VNRT: no hay toolchain P4 ni
hardware ni modelo de software instalado, y aprovisionarlo excede lo que el
entorno del curso permite y el calendario del parcial admite. La opción Ryu/OVS
(opción A) ya está soportada por la infraestructura existente, es lo que el curso
enseña en los laboratorios, y permite llegar a la demo en vivo de R2 durante el
parcial, que es un entregable obligatorio con fecha.

Frente al jurado, esta elección se sostiene con un argumento verificable: se
evaluó la alternativa programable en el plano de datos y se descartó por
disponibilidad del entorno, dejándola como evolución posible para el Ex2 si el
laboratorio habilitara `bmv2` o acceso a Tofino.

## Alternativas evaluadas y descartadas

| Opción | Descripción | Motivo de descarte |
|---|---|---|
| B. P4 sobre Tofino | Detección de R3 en el plano de datos programable | Sin toolchain P4, sin bmv2 y sin Tofino en el VNRT (fase 3). No aprovisionable en el plazo del Ex1 |
| C. Híbrido Ryu + P4 para R3 | Ryu para R1/R2, plano programable para R3 | Depende de bmv2, que no está presente. Se reconsidera para el Ex2 si el entorno cambia |

## Consecuencias

Positivas: el diseño se apoya en infraestructura ya disponible, el contrato de
tablas OpenFlow (`docs/contratos/tablas-openflow.md`) es implementable tal cual
una vez habilitado OF1.3, y el equipo puede concentrarse en la lógica de los
módulos en vez de montar un plano de datos nuevo.

Trabajo que esta decisión genera, ya identificado en el reconocimiento:

1. Habilitar OpenFlow 1.3 en los tres bridges: `ovs-vsctl set bridge <sw>
   protocols=OpenFlow13`. Hoy negocian solo OF1.0 y sin esto Ryu no conecta.
2. Instalar Ryu en el nodo `controller`, que no lo trae.
3. La detección de R3 vive en el plano de control (contar Packet-In en Ryu), con
   la latencia del primer paquete que eso implica. El techo de Packet-In por
   segundo del controlador se medirá en la fase 4 y se llevará al HLD de R3. Si
   ese techo resultara ajustado frente al compromiso de 500 ms, se documenta como
   límite conocido, no invalida la decisión.

Limitación honesta a declarar en el documento: OVS es un switch por software y no
tiene TCAM. El presupuesto de TCAM que pide la rúbrica de R2 se calcula sobre un
modelo de switch de hardware y se presenta por separado de cualquier medición
hecha en OVS.

## Revisión

Se reabre este ADR solo si el entorno del curso habilita un plano de datos
programable antes del Ex2, o si la medición de la fase 4 mostrara que el
controlador no sostiene la carga objetivo, en cuyo caso se evaluaría un
controlador distinto (no un plano de datos distinto).
