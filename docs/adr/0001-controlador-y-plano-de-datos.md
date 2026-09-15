# ADR 0001 — Controlador y plano de datos

- Estado: **PENDIENTE DE DECISIÓN**
- Fecha: por definir
- Decide: Eduardo Rodas (arquitecto), validado con el coach Fernando Guzmán

## Contexto

Hay una inconsistencia entre los avances ya entregados que hay que resolver
antes de escribir el documento de arquitectura del Ex1.

El **AVZ01** dice que el codificador "desarrolla los programas P4 para el entorno
NRT/BNRT sobre Intel Tofino" y que la solución de R3 "debe operar en el entorno
Intel Tofino con lenguaje P4".

El **AVZ02** y el **AVZ03** describen otra cosa: controlador Ryu, switches Open
vSwitch, OpenFlow sobre TCP como southbound, y los tres módulos corriendo como
aplicaciones del controlador.

Son dos arquitecturas distintas, no dos capas de la misma. La rúbrica del Ex1
evalúa "elección de controlador fundamentada" y el jurado va a preguntar por
esto, así que no se puede dejar ambiguo.

## Opciones

### A. Ryu sobre Open vSwitch, todo en el plano de control

La detección de R3 vive en el controlador, que cuenta Packet-In por host y
decide. Es lo que describen AVZ02 y AVZ03.

A favor: es lo que el curso enseña en los laboratorios, corre en el VNRT tal como
está, y el equipo ya tiene la topología levantada. La implementación de R2 para la
demo del parcial es directa.

En contra: la detección depende de que los paquetes suban al controlador, lo que
mete latencia en el primer paquete de cada flujo y pone un techo a la escalabilidad.
El propio AVZ02 ya reconoce esta limitación.

### B. P4 sobre Intel Tofino, detección en el plano de datos

La detección de R3 se programa en el pipeline del switch. El controlador solo
recibe reportes y decide políticas.

A favor: detección a velocidad de línea, tiempos de detección muy por debajo de
los 500 ms comprometidos, y es técnicamente más ambicioso. La rúbrica premia el
"uso creativo de SDN".

En contra: requiere hardware Tofino o un modelo de software (bmv2), que hay que
confirmar si está disponible en el VNRT. Es mucho más trabajo y el riesgo de no
llegar al parcial con algo demostrable es alto.

### C. Híbrido: Ryu como controlador, P4 solo para la detección de R3

Ryu maneja R1 y R2 sobre OVS. R3 se diseña con un plano de datos programable y
se implementa sobre bmv2 si el entorno lo permite.

A favor: concilia los dos avances ya entregados y permite justificar ante el
jurado que la elección responde a los requisitos de cada módulo.

En contra: dos planos de datos distintos en la misma topología complica la
integración y el plan de pruebas.

## Recomendación preliminar

Opción A para el Ex1, dejando la opción C documentada como evolución para el Ex2.

La razón es de riesgo, no de ambición. El parcial pide una demo en vivo del
despliegue de un slice de R2, y llegar a esa demo con OVS y Ryu es realista en
las cuatro semanas que quedan. P4 puede entrar en el documento como alternativa
evaluada y descartada por disponibilidad de entorno, lo que además responde al
criterio de la rúbrica sobre justificación de decisiones de diseño.

## Qué falta para cerrar esta decisión

1. Confirmar con el coach si el VNRT expone algún switch programable o bmv2.
2. Acordarlo con Jeanpier, que es quien lo va a implementar.
3. Actualizar el AVZ04 y el documento de arquitectura con la decisión final.

## Consecuencias

Por definir una vez tomada la decisión.
