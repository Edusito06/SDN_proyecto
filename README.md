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

Laboratorio VNRT. **El gateway de gestión cambia entre sesiones** (hoy
`10.20.12.153`; antes `10.20.11.184`): confírmalo antes de trabajar. Reenvío de
puertos por nodo, ver `docs/lab/acceso-vnrt.md`. Helper: `scripts/vnrt-ssh.sh`.

Las tres redes, **verificadas** en el reconocimiento (no confundirlas, los
avances entregados las tenían cambiadas):

| Red | Función |
|---|---|
| `10.0.0.0/24` | **Plano de datos**: tráfico de usuario, es lo que controla OpenFlow |
| `192.168.0.0/24` | **Gestión**: canal OpenFlow switch↔controlador y acceso SSH |
| `172.16.0.0/24` | Direcciones internas de los bridges OVS; no se usa para control |

Topología real: **estrella con `sw1` al centro** (controlador en sw1; `h1`/`h2` en
sw2; `h3`/`h4` en sw3). Ver `docs/diagramas/topologia-vnrt.md`.

Stack: Open vSwitch 3.3.9 con OpenFlow 1.3, controlador **os-ken** (fork
mantenido de Ryu; Ryu no instala en Python 3.12, ver ADR 0001), Northbound API REST.

## Cómo levantar el entorno

> Estado: `src/`, `topology/` y `tests/` son todavía estructura vacía. Los
> comandos de abajo son el objetivo, no funcionan aún. Lo que **sí** funciona hoy
> son las herramientas de medición en `tools/`.

```bash
# Medición del plano de control (funciona hoy, en el nodo controller)
source ~/ryu-venv/bin/activate
python tools/osken_run.py bench_packetin        # levanta el controlador de medición
python3 tools/loadgen_packetin.py 1000 8        # genera carga desde un host

# Objetivo (aún por implementar)
sudo python3 topology/campus_topo.py
python tools/osken_run.py src/controller/main.py
pytest tests/unit
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
