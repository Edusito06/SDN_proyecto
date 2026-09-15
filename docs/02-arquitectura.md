# Arquitectura de la solución

> Entregable 1 del Ex1. Vale **40 de los 80 puntos** de la primera entrega, más
> que el HLD de los tres requerimientos juntos.
>
> Cada encabezado de este documento corresponde a un criterio de la rúbrica. El
> número entre corchetes es el peso de ese criterio. No borres secciones: si algo
> no aplica, dilo y justifica por qué.
>
> Importante: la rúbrica dice que la evaluación de la arquitectura se centra en
> la solución frente a **los cinco requerimientos**, no solo los tres del grupo.
> Una solución fuerte ante una amenaza pero vulnerable ante otras no se considera
> adecuada. Hay que incluir un análisis cualitativo de cada módulo frente a R1,
> R2, R3, R4 y R5.

## 1. Alcance y contexto

Escenario de campus, población atendida, supuestos y qué queda fuera.

## 2. Elección de controlador fundamentada [8]

Ver `adr/0001-controlador-y-plano-de-datos.md`. Resumir aquí la decisión y el
porqué, con la comparación frente a las alternativas evaluadas.

## 3. Módulos: definición e interacción [14]

Diagrama de módulos y descripción de cada uno. Debe verse la interacción entre
ellos, no solo la lista. El contrato de eventos está en
`contratos/tablas-openflow.md`.

## 4. Justificación de decisiones y trazabilidad a requerimientos [14]

Tabla que conecta cada decisión de diseño con el requerimiento que la motiva.

| Decisión | Requerimiento | Alternativa descartada | Motivo |
|---|---|---|---|
| | | | |

## 5. Separación de planos, reutilización y escalabilidad [14]

Cómo queda separado el plano de control del de datos y qué permite reutilizar
módulos entre requerimientos.

## 6. Uso creativo de SDN [14]

Balanceo dinámico, segmentación avanzada, políticas inteligentes. Aquí es donde
se gana diferenciación frente a los otros grupos.

## 7. Redundancia y tolerancia a fallos del plano de control [4]

Qué pasa si cae el controlador. Modo failsecure o failstandalone del OVS,
controlador secundario, estado persistente.

## 8. Extensibilidad: añadir módulos sin romper lo existente [2]

## 9. Infraestructura

### 9.1 Integración con servicios de campus: DHCP, DNS, autenticación [5]
### 9.2 Capacidad de agregar switches, servidores y enlaces [2]
### 9.3 Crecimiento de usuarios, hosts y VLANs [5]
### 9.4 Recuperación ante caída de nodo o enlace [2]
### 9.5 Enlaces redundantes entre switches y servidores [2]
### 9.6 Ubicación segura de servidores: aislamiento físico y lógico [5]
### 9.7 Minimización de recursos sin comprometer desempeño [4]
### 9.8 Monitoreo de infraestructura física y virtual [5]

## 10. Análisis cualitativo frente a los cinco requerimientos

| Módulo | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| | | | | | |

Para R4 y R5, que no son del grupo, basta con explicar cómo la arquitectura los
acomodaría y qué haría falta añadir.

## 11. Topología propuesta

Diagrama. Direccionamiento: red de acceso `192.168.0.0/24`, red SDN `10.0.0.0/24`
y `172.16.0.0/24`.

## 12. Referencias
