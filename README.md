# TEL354 2026-2 — Grupo 5 — Solución SDN de seguridad de campus

Requerimientos asignados: **R1** (control de acceso por rol), **R2** (restricción de
recursos privilegiados) y **R3** (detección y mitigación de ataques encubiertos,
requerimiento específico de G5).

Coach: Fernando Guzmán. Asesoría: domingos 5 PM.

## Integrantes y roles

| Integrante | Código | Rol | Responsabilidad |
|---|---|---|---|
| Antaurco Corsino, Willian | 20221862 | Líder / Gestor | Coordinación, entregas en Paideia |
| Cuadros David, Jairo Leonardo | 20192676 | Investigador | Estado del arte, sustento técnico |
| Mauricio Cristóbal, Eva María | 20207779 | Testeador / QA | Plan de pruebas, medición de KPIs |
| Gutiérrez Hurtado, Jeanpier Gustavo | 20213805 | Codificador | Implementación de módulos Ryu |
| Rodas Arias, Eduardo | 20227163 | Arquitecto de Solución | Arquitectura, HLD, LLSD, diagramas |

## Estado

| Hito | Fecha | Estado |
|---|---|---|
| AVZ01 Rol de integrantes | 27 ago | Entregado |
| AVZ02 Concepto de operación | 29 ago | Entregado |
| AVZ03 Casos de uso | 3 set | Entregado |
| AVZ04 Bosquejo de arquitectura | sem 4 | Pendiente |
| Presentación HLD R1 y R2 (clase) | jue 17 set | Pendiente |
| Lab 3, borrador de arquitectura | sem 6 | Pendiente |
| Presentación arquitectura y módulos | jue 8 oct | Pendiente |
| **Ex1, primera entrega calificada** | sem del 12 al 17 oct | Pendiente |

## Entregables del Ex1 (los cinco son independientes)

1. Arquitectura de la solución, en PDF.
2. High Level Design en PDF de R1, R2 y R3.
3. Copia de la presentación.
4. Código actual, **con énfasis en el de R2**.
5. Demo en vivo durante el parcial: despliegue de un slice predefinido (R2).

## Entorno

Laboratorio VNRT. Gateway de gestión `10.20.11.184` con reenvío de puertos
(Controller 5800, SW1 5801, H1 5811). Red de acceso `192.168.0.0/24`.
Red SDN `10.0.0.0/24` y `172.16.0.0/24`, no enrutable desde fuera.

Stack: Open vSwitch con OpenFlow 1.3, controlador Ryu, Northbound API REST.

## Cómo levantar el entorno

```bash
sudo python3 topology/campus_topo.py        # levanta namespaces y bridges OVS
ryu-manager src/controller/main.py          # levanta el controlador
pytest tests/unit                           # pruebas unitarias
sudo python3 tests/integration/run_scan.py  # escenario de ataque y métricas
```

## Estructura

```
docs/         diseño: arquitectura, HLD, LLSD, plan de pruebas, decisiones (ADR)
src/          código del controlador Ryu y la API REST
topology/     scripts que levantan la topología de laboratorio
tests/        unitarias e integración (escenarios de ataque + medición)
entregables/  avances semanales y PDFs de entrega
scripts/      utilidades: exportar a PDF, crear issues desde la rúbrica
```

## Convenciones

Ramas: `main` (protegida) ← `develop` ← `feature/<descripción>`.
Commits: `tipo(alcance): descripción corta`, con tipos `feat`, `fix`, `docs`,
`test`, `chore`. Todo entra por Pull Request con revisión de al menos un
integrante. El historial de PRs es la evidencia de trabajo coordinado que la
rúbrica del Ex1 califica con peso 20.
