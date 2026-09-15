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

## Dónde está cada cosa

Todo el contexto necesario está en este repositorio. No dependas de nada externo.

| Archivo | Qué contiene |
|---|---|
| `README.md` | Estado, integrantes, calendario y entregables del Ex1 |
| `docs/referencia/` | Enunciado del proyecto, sílabo y rúbrica del Ex1 en PDF |
| `docs/02-arquitectura.md` | Plantilla de arquitectura, cada sección es un criterio de la rúbrica con su peso |
| `docs/03-hld/` | HLD de R1, R2 y R3, igualmente mapeados a la rúbrica |
| `docs/contratos/tablas-openflow.md` | Pipeline de tablas, prioridades por módulo, metadata y eventos. **Es el documento que manda** |
| `docs/adr/` | Decisiones de arquitectura. La 0001 está pendiente |
| `docs/lab/` | Runbook de reconocimiento del VNRT y sus resultados |
| `entregables/avances/` | AVZ01 a AVZ03 ya entregados en Paideia, y la plantilla semanal |
| `GUIA-GITHUB.md` | Cómo subir al repo del grupo y montar el tablero |

Los avances AVZ01 a AVZ03 en PDF son la mejor fuente sobre lo ya decidido:
roles del equipo, concepto de operación, casos de uso CU-01 y CU-02, KPIs
comprometidos y restricciones del entorno. Léelos antes de proponer diseño.

## Estado actual y qué sigue

El repositorio está recién montado. El trabajo inmediato es el runbook
`docs/lab/00-reconocimiento-vnrt.md`, que levanta los datos del entorno VNRT
necesarios para cerrar el ADR 0001 sobre la elección de controlador y plano de
datos. Esa decisión bloquea el HLD de R3 y buena parte de la arquitectura.

## Stack

OpenFlow 1.3 sobre Open vSwitch, controlador Ryu en Python, Northbound API REST.
Entorno de laboratorio VNRT. Esta elección está **pendiente de confirmación** en
el ADR 0001: el AVZ01 menciona P4 sobre Intel Tofino y los AVZ02 y AVZ03
describen Ryu sobre OVS. No la des por cerrada hasta que el ADR diga lo
contrario.

## Entorno VNRT

Gateway de gestión `10.20.11.184` con reenvío de puertos: Controller 5800,
SW1 5801, H1 5811. Red de acceso `192.168.0.0/24`. Red SDN `10.0.0.0/24` y
`172.16.0.0/24`, no enrutable desde fuera. Los comandos de OVS corren en el
namespace por defecto; los de hosts virtuales necesitan `ip netns exec`.

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
   R2 y R3 se pisen en el switch. Si algo obliga a cambiarlo, se abre un ADR;
   no se edita el contrato por cuenta propia.
4. **Una rama, un módulo, un responsable.** No trabajar en paralelo sobre los
   mismos archivos. Ramas `feature/<descripción>` desde `develop`, merge por
   Pull Request.
5. **Cada KPI que aparezca en un documento debe ser medible** por un script en
   `tests/integration/`. Nada de números inventados: la rúbrica premia el
   análisis cuantitativo con datos reales. Si una medición no se pudo hacer, se
   escribe que no se pudo y por qué.
6. **Nunca commitear** credenciales, certificados, perfiles de conexión del
   VNRT ni capturas con datos personales.
7. **El VNRT es un entorno compartido del curso.** No instalar paquetes ni
   cambiar configuración global sin preguntar. No tocar bridges, flujos ni
   namespaces que no hayas creado tú.
8. **Los ataques de prueba solo dentro de la topología del laboratorio**, contra
   hosts virtuales propios. Nunca contra la red de la universidad ni contra
   ninguna IP fuera del entorno.

## KPIs comprometidos (AVZ02)

| Métrica | Objetivo |
|---|---|
| Tasa de detección de escaneos | ≥ 95% |
| Tiempo de detección | ≤ 500 ms |
| Falsos positivos sobre usuarios legítimos | ≤ 2% |
| Uso de CPU del controlador bajo 100 flujos/s | ≤ 60% |
| Entradas de TCAM de mitigación activas | ≤ 50 |

Ojo: OVS es software y **no tiene TCAM**. El presupuesto de TCAM es un cálculo
analítico sobre un modelo de switch de hardware, no algo que se mida en el
laboratorio. No presentes mediciones de OVS como si fueran números de TCAM.

## Qué NO debe hacer un agente

- Tomar decisiones de arquitectura por su cuenta. Se proponen como ADR y las
  aprueba el arquitecto de solución (Eduardo), porque son las que el jurado
  pregunta en la sustentación oral.
- Inventar resultados de pruebas o métricas, o presentar datos de la literatura
  como si fueran medidos aquí.
- Reescribir documentos de avance ya entregados en Paideia (`entregables/avances/`
  con número menor al actual). Son registro histórico.
