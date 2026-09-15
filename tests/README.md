# Pruebas

## Unitarias (`unit/`)

Lógica pura de cada módulo, sin red. Corren en el CI en cada Pull Request.

## Integración (`integration/`)

Levantan la topología real, ejecutan un escenario y miden. Son las que producen
los números del análisis cuantitativo, así que cada KPI declarado en un documento
tiene que tener aquí un script que lo mida.

| Script previsto | Qué mide | KPI asociado |
|---|---|---|
| `test_contrato_tablas.py` | Que ningún módulo escriba fuera de su tabla o rango de prioridad | Integridad del pipeline |
| `run_scan.py` | Escaneo con nmap, tiempo hasta el bloqueo | Detección ≥ 95%, latencia ≤ 500 ms |
| `run_spoof.py` | IP spoofing con hping3 | Detección de suplantación |
| `run_flood.py` | Muchos a uno contra un servidor | Tiempo de mitigación |
| `run_legitimo.py` | Tráfico normal intenso | Falsos positivos ≤ 2% |
| `medir_recursos.py` | CPU del controlador y entradas de TCAM ocupadas | CPU ≤ 60%, TCAM ≤ 50 |

## Regla

Cada corrida escribe sus resultados crudos en `resultados/raw/` (ignorado por git)
y un resumen agregado en `resultados/` que sí se versiona. Nunca se escribe a mano
un número en un documento: se cita el resumen generado.
