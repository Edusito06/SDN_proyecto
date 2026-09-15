# Contexto del proyecto para asistentes de IA

Lee este archivo antes de tocar nada. Resume las reglas del proyecto para que
cualquier agente trabaje sin descarrilarse.

## Qué es

Proyecto del curso TEL354 (Redes Definidas por Software), PUCP, ciclo 2026-2,
Grupo 5. Se diseña e implementa una solución SDN de seguridad para una red de
campus universitario. Al grupo le tocan tres requerimientos: R1, R2 y R3.

- **R1**: controlar el acceso a la red de usuarios válidos según su rol.
- **R2**: restringir el acceso a recursos privilegiados solo a autorizados.
- **R3**: detectar y mitigar ataques encubiertos en la intranet, principalmente
  network scanning, port scanning e IP spoofing. Es el requerimiento específico
  de G5 y vale el doble que los otros dos.

## Stack fijo

OpenFlow 1.3 sobre Open vSwitch, controlador Ryu en Python, Northbound API REST.
Entorno de laboratorio VNRT. No cambiar de controlador sin escribir antes un ADR
en `docs/adr/` y discutirlo con el coach.

## Reglas de trabajo

1. **El diseño va antes que el código.** El curso evalúa arquitectura y HLD con
   más peso que la implementación en el Ex1. Si un cambio de código contradice
   lo que dice `docs/`, se actualiza el documento en el mismo Pull Request.
2. **Todo documento se escribe en Markdown** dentro de `docs/`. Los PDF se
   generan con `scripts/md-a-pdf.sh` recién al momento de entregar. No editar
   PDFs a mano ni mantener versiones en Word.
3. **El contrato de tablas y prioridades OpenFlow manda.** Está en
   `docs/contratos/tablas-openflow.md`. Ningún módulo instala reglas fuera del
   rango de prioridad que le corresponde. Esta es la causa número uno de que
   R2 y R3 se pisen en el switch.
4. **Una rama, un módulo, un responsable.** No trabajar en paralelo sobre los
   mismos archivos.
5. **Cada KPI que aparezca en un documento debe ser medible** por un script en
   `tests/integration/`. Nada de números inventados: la rúbrica premia el
   análisis cuantitativo con datos reales.
6. **Nunca commitear** credenciales, certificados, perfiles de conexión del
   VNRT ni capturas con datos personales.

## KPIs comprometidos (AVZ02)

| Métrica | Objetivo |
|---|---|
| Tasa de detección de escaneos | ≥ 95% |
| Tiempo de detección | ≤ 500 ms |
| Falsos positivos sobre usuarios legítimos | ≤ 2% |
| Uso de CPU del controlador bajo 100 flujos/s | ≤ 60% |
| Entradas de TCAM de mitigación activas | ≤ 50 |

## Qué NO debe hacer un agente

- Tomar decisiones de arquitectura por su cuenta. Se proponen como ADR y las
  aprueba el arquitecto de solución (Eduardo), porque son las que el jurado
  pregunta en la sustentación oral.
- Inventar resultados de pruebas o métricas.
- Reescribir documentos de avance ya entregados en Paideia (`entregables/avances/`
  con número menor al actual). Son registro histórico.
