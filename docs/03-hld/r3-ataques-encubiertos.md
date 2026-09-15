# HLD R3 — Detección y mitigación de ataques encubiertos en la intranet

> Requerimiento específico de G5. Vale **20 puntos** del Ex1, el doble que R1 y
> R2 por separado. Es donde más se gana y más se pierde.
>
> Los números entre corchetes son los pesos de la rúbrica del Ex1.

## 1. Definición y delimitación de la amenaza [10]

Los tres vectores del enunciado:

- **Network scanning**: barrido de direcciones para descubrir hosts vivos.
- **Port scanning**: barrido de puertos en un host para descubrir servicios.
- **IP spoofing**: suplantación de la dirección de origen.
- **Ataques de muchos a uno**: bots enviando requests maliciosos a un servidor.

Para cada uno: qué lo caracteriza en el tráfico y por qué es "encubierto", es
decir, por qué no se distingue trivialmente del tráfico normal.

## 2. Análisis del entorno afectado y alcance [8]

Qué es la intranet en este diseño y hasta dónde llega la solución. Qué queda
fuera y por qué, sobre todo la frontera con R5.

## 3. Diseño lógico del mecanismo de detección [12]

Para escaneo, el AVZ02 ya define el principio: contar Packet-In por host en una
ventana de tiempo y marcar como anómala la actividad hacia muchas IP o puertos
inexistentes. Falta formalizarlo.

| Parámetro | Símbolo | Valor propuesto | Justificación |
|---|---|---|---|
| Ventana de observación | T | | |
| Umbral de destinos distintos | N_dst | | |
| Umbral de puertos distintos | N_port | | |
| Umbral de Packet-In fallidos | N_miss | | |

Para IP spoofing, la detección es estructural y no estadística: se compara la
terna IP origen, MAC origen y puerto de ingreso contra lo aprendido. Una
discrepancia revela suplantación. Esto vive en la tabla 0 del pipeline.

Decisión abierta que conviene documentar: umbrales fijos o detección de anomalías
basada en aprendizaje. La rúbrica menciona explícitamente "ML-based anomaly
detection" como opción válida. Si se descarta, hay que justificar por qué.

## 4. Justificación tecnológica y pertinencia de herramientas [4]

## 5. Capacidad de detección temprana [8]

## 6. Tiempo estimado de detección [3]

Compromiso del AVZ02: **≤ 500 ms** desde el primer Packet-In anómalo hasta la
instalación de la regla de bloqueo. Hay que sustentar de dónde sale ese número,
no solo declararlo.

## 7. Diseño del proceso de mitigación [12]

Escalera de respuesta, que es más defendible que un bloqueo binario:

| Nivel | Condición | Acción | Duración |
|---|---|---|---|
| 1 | Sospecha inicial | Limitar tasa con meter OpenFlow | corta |
| 2 | Ataque confirmado | Descartar tráfico del host | media |
| 3 | Reincidencia | Revocar sesión vía R1 y propagar a todos los switches vía R2 | hasta intervención del administrador |

## 8. Tiempo estimado de mitigación [3]

## 9. Variedad de ataques detectados y fracción de tráfico malicioso que pasa [8]

## 10. Flexibilidad y escalabilidad del diseño [8]

Cómo se añade un vector de ataque nuevo sin rehacer el módulo.

## 11. Identificación de patrones anómalos dentro de la intranet [12]

## 12. Mecanismos de detección elegidos [12]

IDS, detección de anomalías, políticas de flujo SDN. Cuál se usa para qué vector.

## 13. Documentación de respuesta a incidentes

Cómo se registra un incidente, cómo se notifica y cómo se evalúa después. La
rúbrica lo pide y suele olvidarse.

## 14. Interfaz con los otros módulos

R3 es dueño de las tablas 0 y 1, con prioridades 50000 a 59999. Emite
`ataque_detectado` y `mitigacion_aplicada`. Consume `host_autenticado` de R1 para
conocer la terna legítima y `acceso_denegado` de R2 como señal temprana: un host
que acumula accesos denegados es sospechoso antes de que empiece a escanear.

## 15. Métricas comprometidas

| Métrica | Objetivo | Cómo se mide |
|---|---|---|
| Tasa de detección de escaneos | ≥ 95% | `tests/integration/run_scan.py` |
| Tiempo de detección | ≤ 500 ms | |
| Falsos positivos | ≤ 2% | |
| Tiempo de mitigación | | |
| CPU del controlador bajo 100 flujos/s | ≤ 60% | |
| Entradas de TCAM de mitigación | ≤ 50 | |

## 16. Restricción de TCAM

Limitación ya identificada en el AVZ02: una entrada por IP atacante llena la tabla
rápido y los TCAM misses aumentan la latencia. La mitigación usa máscaras que
cubren rangos, no hosts individuales, y toda regla lleva timeout.
