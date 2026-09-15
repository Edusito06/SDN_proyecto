# Contrato de tablas y prioridades OpenFlow

Este es el documento más importante del repositorio para poder trabajar en
paralelo. Define qué tabla y qué rango de prioridad le toca a cada módulo, de
modo que R1, R2 y R3 puedan desarrollarse por separado sin que sus reglas se
pisen dentro del switch.

Ningún módulo instala una regla fuera de su rango. Cualquier cambio a este
contrato se discute con todo el grupo antes de implementarse.

## Pipeline de tablas

El paquete recorre las tablas en orden. Cada tabla decide si descarta, si
responde o si pasa el paquete a la siguiente con `goto_table`.

| Tabla | Nombre | Dueño | Qué hace |
|---|---|---|---|
| 0 | Ingreso y anti-spoofing | R3 | Valida la terna IP origen, MAC origen y puerto de ingreso contra lo aprendido. Si no coincide, es spoofing y se descarta. |
| 1 | Mitigación activa | R3 | Bloqueos dinámicos de hosts confirmados como atacantes. Corta lo antes posible para no gastar el resto del pipeline. |
| 2 | Identidad y rol | R1 | Identifica al host y escribe su rol en `metadata`. Si no lo conoce, genera Packet-In hacia el controlador. |
| 3 | Política de recursos | R2 | Con el rol ya en `metadata`, decide si el acceso al recurso privilegiado procede o se descarta. |
| 4 | Reenvío | común | Conmutación L2 aprendida y salida por el puerto correspondiente. |

## Rangos de prioridad

Los rangos son excluyentes. Cada módulo escribe solo dentro del suyo.

| Rango | Dueño | Uso |
|---|---|---|
| 60000 a 65535 | Administrador | Reglas de emergencia manuales. Ningún módulo escribe aquí. |
| 50000 a 59999 | R3 | Bloqueo y limitación de tasa de atacantes confirmados. |
| 40000 a 49999 | R2 | Denegaciones explícitas de recursos privilegiados. |
| 30000 a 39999 | R2 | Permisos explícitos de recursos privilegiados. |
| 20000 a 29999 | R1 | Reglas derivadas del rol del usuario. |
| 10000 a 19999 | común | Reenvío L2 aprendido. |
| 1 a 9999 | común | Reglas por defecto y agregados de baja especificidad. |
| 0 | común | Table-miss. Envía Packet-In al controlador. |

## Codificación de `metadata`

R1 escribe el rol del host en los bits bajos de `metadata`. R2 lo lee. Nadie
más lo modifica.

| Bits | Campo | Valores |
|---|---|---|
| 0 a 3 | Rol | 0 desconocido, 1 alumno, 2 docente, 3 administrador, 4 superusuario |
| 4 a 7 | Estado de sesión | 0 sin autenticar, 1 autenticado, 2 revocado por R3 |
| 8 a 63 | Reservado | Sin uso por ahora |

## Presupuesto de TCAM

El compromiso del grupo es no superar **50 entradas de mitigación activas**
simultáneas, y que el total por switch se mantenga holgado frente a la capacidad
del OVS.

Para lograrlo, las reglas de R3 cumplen dos condiciones. Primero, usan máscaras
que cubren rangos o subredes en lugar de una entrada por host atacante, porque el
peor caso de expansión de un rango arbitrario en prefijos es de 2n menos 2
entradas y eso hace explotar la tabla. Segundo, toda regla de mitigación se
instala con `idle_timeout` y `hard_timeout`, nunca permanente, de modo que la
tabla se autolimpia sola.

Estimación a documentar en el HLD de R2, porque la rúbrica lo pide de forma
explícita con peso 10: número máximo de entradas TCAM esperadas por switch,
desglosado por módulo.

## Contrato de eventos entre módulos

Los módulos no se llaman directamente entre sí. Publican eventos en un bus
interno del controlador. Así cada uno se puede desarrollar y probar aislado.

| Evento | Emisor | Receptores | Carga útil |
|---|---|---|---|
| `host_autenticado` | R1 | R2, R3 | dpid, puerto, MAC, IP, rol |
| `sesion_revocada` | R1 | R2, R3 | MAC, IP, motivo |
| `acceso_denegado` | R2 | R3 | MAC origen, IP destino, recurso |
| `ataque_detectado` | R3 | R1, R2 | MAC, IP, tipo de ataque, confianza, marca de tiempo |
| `mitigacion_aplicada` | R3 | R1, R2 | MAC, IP, acción, ttl |

El flujo que ya está descrito en el AVZ03 encaja así: R3 detecta un escaneo,
emite `ataque_detectado`, R1 reacciona revocando la sesión y R2 reacciona
propagando el bloqueo al resto de switches.

## Cómo se verifica que se cumple

`tests/integration/test_contrato_tablas.py` levanta la topología, hace que los
tres módulos instalen reglas y verifica con `ovs-ofctl dump-flows` que ninguna
regla quedó fuera de su rango de prioridad ni en una tabla ajena.
