# HLD R1 — Control de acceso a la red según rol

> Vale **10 puntos** del Ex1. Se expone en clase el jueves 17 de setiembre junto
> con R2, 15 minutos, y esa exposición cuenta como nota del laboratorio de la
> semana 5.
>
> Los números entre corchetes son los pesos de la rúbrica del Ex1.
>
> **Convención de este documento:** los valores marcados como *medido* provienen
> de `../lab/resultados-vnrt.md` y son reproducibles con los comandos allí
> listados. Los marcados como *objetivo* son compromisos del AVZ02 aún no
> verificados. Los marcados como *analítico* son cálculos sobre un modelo, no
> mediciones.

## 0. Contexto de red (corregido contra el entorno real)

El reconocimiento del VNRT (fases 1 a 4) corrigió un supuesto del AVZ03: hay dos
redes y cumplen papeles distintos.

| Red | Rol real | Evidencia |
|---|---|---|
| `192.168.0.0/24` | **Gestión.** Por aquí va el canal OpenFlow switch↔controlador y el acceso SSH. **No** es la red de usuario | Fase 4: `set-controller tcp:192.168.0.10:6653` conecta; el plano de datos no alcanza al controlador sin flujos |
| `10.0.0.0/24` | **Plano de datos.** Es el tráfico de usuario que R1, R2 y R3 controlan con OpenFlow | Fase 1: `h1..h4` tienen `ens4` en 10.0.0.1-.4, enclavadas al datapath OVS |
| `172.16.0.0/24` | Direcciones internas de los bridges OVS. **No se usa** para el canal de control | Fase 1/4 |

Todo lo que sigue opera sobre `10.0.0.0/24`. Donde el CU-01 dice "red de acceso
192.168.0.0/24" debe leerse `10.0.0.0/24`; la corrección está registrada en los
resultados de laboratorio.

## 1. Lógica de acceso y autenticación de usuarios válidos [16]

### Decisión

**La identidad del host se establece por su dirección MAC, contrastada contra una
tabla de roles precargada en el controlador.** Es la decisión del CU-01 ya
entregado y se mantiene, declarada explícitamente como **alcance de laboratorio**.

### Flujo de identificación

1. El host emite su primer paquete en `10.0.0.0/24`.
2. El paquete llega a la tabla 2 del pipeline (identidad y rol) sin coincidencia
   y genera un `Packet-In` hacia el controlador.
3. R1 extrae la MAC origen y la busca en la tabla de roles.
4. Si la MAC está registrada, obtiene el rol; si no, aplica **rol mínimo por
   defecto** (alumno) y registra el evento para auditoría.
5. R1 instala un `FLOW_MOD` en la tabla 2 que escribe el rol en `metadata` y
   pasa el paquete a la tabla 3 con `goto_table`.
6. Emite el evento `host_autenticado` en el bus interno.

### Por qué MAC y no 802.1X, y cómo se compensa la debilidad

La MAC es **suplantable**, y el jurado lo va a señalar. Lo asumimos de frente y
el diseño lo compensa por construcción, en lugar de ignorarlo:

| Limitación de identificar por MAC | Cómo la compensa la arquitectura |
|---|---|
| Un atacante puede clonar la MAC de un docente | La **tabla 0 de R3** valida la terna (IP origen, MAC origen, **puerto físico de ingreso**). Una MAC clonada que aparece por un puerto distinto al aprendido se descarta como spoofing antes de llegar a la tabla de identidad |
| No hay prueba criptográfica de identidad | El alcance del Ex1 es la lógica de control de acceso SDN, no la infraestructura de credenciales. Se declara como supuesto, no se disimula |
| No hay caducidad de sesión | R1 mantiene estado de sesión en `metadata` (bits 4-7) y R3 puede forzar `sesion_revocada` |

**Este es el argumento fuerte de la exposición:** el par MAC + puerto de ingreso
es un identificador considerablemente más difícil de falsificar que la MAC sola,
y sale gratis porque R3 ya necesita esa validación para detectar IP spoofing. La
debilidad de R1 se cubre con un módulo que de todos modos teníamos que construir.

### Evolución prevista

802.1X con RADIUS es la evolución natural y **no rompe este diseño**: sustituye
únicamente el paso 3 (de "buscar MAC en tabla" a "resultado de la autenticación
EAP"). El resto del pipeline —escritura de rol en `metadata`, tablas, prioridades,
eventos— queda igual. Se documenta como trabajo del Ex2.

## 2. Definición de usuarios, niveles de acceso y permisos [16]

Cuatro roles, alineados con la codificación de `metadata` del contrato de tablas
(`../contratos/tablas-openflow.md`). Sin superposiciones y sin vacíos: todo host
cae exactamente en un rol, y el rol 0 (desconocido) degrada a alumno.

| Valor en `metadata` | Rol | Nivel | Permisos sobre la red | Recursos accesibles |
|---|---|---|---|---|
| 1 | **Alumno** | Mínimo | Solo consumo. No administra nada | Portal académico y servicios generales. **Denegado** en notas y repositorio de exámenes |
| 2 | **Docente** | Medio | Consumo + acceso a evaluación | Todo lo del alumno + **servidor de notas** (lectura/escritura) |
| 3 | **Administrador de red** | Alto | Define y ajusta políticas vía Northbound API, revoca sesiones, consulta métricas. **No** accede a datos académicos | Plano de gestión y telemetría. **Denegado** en notas y exámenes (separación de funciones) |
| 4 | **Superusuario** | Máximo | Todo lo anterior, sin restricción | Todos, incluido el **repositorio de exámenes** |
| 0 | *(desconocido)* | — | Degrada a alumno y se registra el evento | Los del alumno |

Nota de diseño deliberada: el **administrador de red no tiene acceso a los datos
académicos**. Administrar la red y leer notas son funciones distintas; darle todo
al administrador sería un vacío de control que la rúbrica penaliza. El acceso
total existe solo en el superusuario, que es un rol de excepción y auditado.

### Matriz rol × recurso (vista de R1; el detalle vive en R2)

| Recurso | Alumno | Docente | Admin. de red | Superusuario |
|---|---|---|---|---|
| Portal académico / servicios generales | ✔ | ✔ | ✔ | ✔ |
| Servidor de notas (`10.0.0.3`) | ✘ | ✔ | ✘ | ✔ |
| Repositorio de exámenes (`10.0.0.4`) | ✘ | ✘ | ✘ | ✔ |
| Northbound API de gestión | ✘ | ✘ | ✔ | ✔ |

## 3. Pertinencia técnica del método de control [10]

Se evalúan cuatro mecanismos y se adopta **RBAC aplicado mediante políticas
OpenFlow**, con la identidad resuelta en el controlador.

| Mecanismo | Qué aportaría | Por qué no se adopta como base |
|---|---|---|
| **ACL estáticas** en los switches | Simple, sin controlador | No hay noción de identidad ni de rol: la ACL ata permisos a IP/puerto, que cambian. Ingobernable al crecer y no reacciona a eventos de R3 |
| **RADIUS/802.1X** | Autenticación fuerte y estándar | Resuelve *quién entra*, pero **no** *qué puede alcanzar* dentro de la red. Es complementario, no sustituto. Además no hay RADIUS en el VNRT |
| **ABAC** (por atributos) | Políticas muy expresivas (hora, ubicación, postura) | Complejidad de evaluación y de prueba desproporcionada para 4 roles y un parcial. Se menciona como evolución |
| **RBAC sobre OpenFlow** ← *adoptado* | El rol viaja en `metadata` dentro del pipeline y se aplica en el switch a velocidad de línea | — |

Razones de la elección, en orden de peso:

1. **El rol se aplica en el plano de datos, no en el controlador.** Solo el
   primer paquete sube; el resto se conmuta en el switch. Esto es lo que hace que
   la latencia sea de milisegundos (§7) y no crezca con el número de usuarios.
2. **Encaja con el contrato de tablas.** `metadata` es exactamente el mecanismo
   que OpenFlow 1.3 ofrece para pasar contexto entre tablas, y el reconocimiento
   confirmó que está soportado (fase 2: `write_metadata` + `goto_table` OK).
3. **Es reactivo.** Al vivir la decisión en el controlador, R1 puede revocar una
   sesión cuando R3 emite `ataque_detectado`. Una ACL estática no puede.

## 4. Lógica del proceso desde solicitud hasta autorización [16]

```
 h1 (alumno)         sw2 (OVS, OF1.3)        Controlador os-ken        Tabla de roles
 10.0.0.1            dpid 00001a749039894a    192.168.0.10:6653         (en memoria)
    |                       |                         |                       |
    |--1. primer paquete--->|                         |                       |
    |                       | tabla 0 (R3): terna     |                       |
    |                       |   IP+MAC+puerto OK      |                       |
    |                       | tabla 1 (R3): sin       |                       |
    |                       |   bloqueo activo        |                       |
    |                       | tabla 2 (R1): MISS      |                       |
    |                       |                         |                       |
    |                       |--2. Packet-In (OFPR_NO_MATCH)-->|               |
    |                       |                         |--3. buscar MAC------->|
    |                       |                         |<--4. rol=1 (alumno)---|
    |                       |<--5. FLOW_MOD-----------|                       |
    |                       |   tabla 2, prio 20000-29999                     |
    |                       |   match: eth_src=MAC(h1)                        |
    |                       |   acciones: write_metadata(rol=1, sesion=1)      |
    |                       |             goto_table:3                        |
    |                       |<--6. BarrierReply------>|                       |
    |                       |                         |                       |
    |                       |         [evento host_autenticado -> R2, R3]     |
    |                       |                         |                       |
    |--7. paquetes siguientes-->| tabla 2 ACIERTA: metadata escrita           |
    |                       | tabla 3 (R2): política de recurso               |
    |                       | tabla 4: reenvío                                |
    |<--8. tráfico conmutado en el switch, sin subir al controlador---------->|
```

Puntos que conviene remarcar en la exposición:

- **El costo del control lo paga solo el primer paquete.** Los pasos 2 a 6
  ocurren una vez por host; el paso 7 en adelante se resuelve en el switch.
- **El orden de tablas no es arbitrario.** R3 valida antispoofing (tabla 0)
  *antes* de que R1 asigne identidad (tabla 2), justamente para que un atacante no
  pueda obtener un rol suplantando una MAC. Es la coherencia que responde a la
  objeción de §1.
- **Flujo alternativo:** MAC no registrada → rol alumno + evento de auditoría.
  **Flujo de excepción:** llega `ataque_detectado` de R3 → R1 reescribe `metadata`
  con sesión revocada (valor 2) y emite `sesion_revocada`.

## 5. Multiplataforma y portabilidad [10]

| Capa | Atadura al VNRT | Qué haría falta para llevarlo a otro entorno |
|---|---|---|
| **Protocolo** | Ninguna. OpenFlow 1.3 es estándar multi-fabricante | Nada. Verificado que OVS negocia OF1.0-1.5 (fase 2) |
| **Pipeline de tablas** | Ninguna en el diseño; requiere ≥5 tablas y `metadata` | Los switches reales ofrecen menos tablas que OVS (254 medidas). Si un modelo ofreciera menos de 5, hay que fusionar tablas conservando el orden |
| **Controlador** | Media. El código usa la API `os_ken.*` | Portar a otro controlador implica reescribir los manejadores de eventos, no el diseño. El pipeline y las prioridades se mantienen |
| **Identidad por MAC** | Ninguna | Sustituible por 802.1X sin tocar el resto (§1) |
| **Direccionamiento** | Alta en los valores concretos (10.0.0.0/24) | Parametrizar subredes en configuración, no incrustarlas en el código |

**Riesgo honesto a declarar:** el diseño asume `metadata` y múltiples tablas.
Ambas son de OpenFlow 1.3; un equipo limitado a OpenFlow 1.0 **no** puede
ejecutar este pipeline. Lo comprobamos en carne propia: los bridges del VNRT
venían configurados en OF1.0 y hubo que habilitar 1.3 explícitamente.

## 6. Escalabilidad: logins por segundo [10]

Cifras **medidas** en el VNRT (fase 4, `tools/bench_packetin.py` sobre el nodo
`controller`: 2 vCPU, 1.9 GiB). Una autenticación consume, como mínimo, un
`Packet-In` y un `FLOW_MOD`, que es exactamente el ciclo que mide el banco.

| Carga ofrecida | Eventos procesados | CPU del controlador | Pérdida |
|---|---|---|---|
| 100 /s | 100 /s | 4 % | 0 |
| 500 /s | 500 /s | 17-20 % | 0 |
| 1 000 /s | 1 000 /s | 32-34 % | 0 |
| 2 000 /s | 2 000 /s | 47-52 % | 0 |
| 4 000 /s | 4 000 /s | 53-67 % | 0 |
| ~93 000 /s (saturación) | **~11 000 /s (techo)** | ~110 % (núcleo saturado) | masiva |

**Conclusión de escalabilidad:**

- **Techo duro medido: ~11 000 autenticaciones/s.** Por encima, el controlador
  pierde eventos.
- **Techo operativo recomendado: ~4 000 autenticaciones/s**, que es donde la CPU
  se mantiene en torno al 60 % comprometido en el AVZ02.
- Para dimensionar: un campus con 10 000 usuarios que se conectan en la hora pico
  a lo largo de 10 minutos genera del orden de **17 autenticaciones/s de media**.
  El margen frente al techo operativo es de más de dos órdenes de magnitud.

**Dónde está el cuello de botella, con evidencia:** en el **plano de control**, y
concretamente en que os-ken es monohilo (eventlet). En saturación un núcleo llega
al 100 % mientras el segundo queda ocioso. La vía de crecimiento no es una
máquina más grande, sino **repartir switches entre varias instancias de
controlador**. El plano de datos no es el límite: instalar reglas cuesta ~140 µs
y OVS aceptó 50 000 reglas sin rechazar ninguna (fase 2).

## 7. Latencia con múltiples usuarios [11]

Latencia **medida** del ciclo `Packet-In` → `FLOW_MOD` confirmado con `Barrier`,
que es exactamente la latencia de autenticación del primer paquete.

| Carga concurrente | Latencia mediana | Latencia p95 | ¿Cumple el objetivo de 500 ms? |
|---|---|---|---|
| 100 /s | **1.45 ms** | 1.45 ms | Sí, con 344× de margen |
| 500 /s | ~1.2 ms | ~1.56 ms | Sí |
| 1 000 /s | ~0.95 ms | ~1.5 ms | Sí |
| 2 000 /s | ~0.91 ms | ~1.5 ms | Sí |
| 4 000 /s | ~0.87 ms | ~1.6 ms | Sí |
| Saturación (~11 000 /s) | ~0.9-1.2 ms | **175 ms → 4 100 ms** | **No** |

Lecturas importantes:

1. **La latencia no se degrada con la concurrencia** mientras el controlador no
   sature: entre 100 y 4 000 autenticaciones/s se mantiene por debajo de 2 ms.
   La razón es de diseño: solo el primer paquete sube al controlador.
2. **La degradación no es gradual, es un acantilado.** Al saturar, la mediana
   sigue baja pero el **p95 se dispara a segundos**: la cola de `Packet-In` se
   acumula. Por eso el indicador a vigilar en producción es el **p95, no el
   promedio** — un promedio sano puede esconder que un 5 % de los usuarios espera
   4 segundos.
3. El usuario percibe esta latencia **una sola vez**, al conectarse. El tráfico
   posterior se conmuta en el switch sin costo de control.

## 8. Supervisión del correcto funcionamiento [11]

### Qué se registra

| Evento | Cuándo | Para qué sirve |
|---|---|---|
| `host_autenticado` | Cada asignación de rol | Auditoría de quién entró, con qué rol, por qué puerto |
| MAC desconocida | Rol mínimo por defecto | Detectar equipos no inventariados |
| `sesion_revocada` | R3 confirma ataque | Trazabilidad de la respuesta automática |
| Rechazo en tabla 0 | Terna IP/MAC/puerto inconsistente | Señal temprana de suplantación |

### Cómo se expone (Northbound API REST)

| Endpoint | Devuelve |
|---|---|
| `GET /r1/sesiones` | Hosts autenticados: MAC, IP, rol, dpid, puerto, antigüedad |
| `GET /r1/metricas` | Autenticaciones/s, latencia mediana y p95, CPU, sesiones activas |
| `GET /r1/roles` | Tabla de roles vigente |
| `POST /r1/revocar` | Revocación manual por el administrador de red |

### Verificación continua

El indicador de salud del módulo es la **coherencia entre estado y plano de
datos**: para cada sesión activa debe existir su regla en la tabla 2, dentro del
rango 20000-29999. Se comprueba con `ovs-ofctl dump-flows` y es lo que valida
`tests/integration/test_contrato_tablas.py`. Una sesión sin regla, o una regla
fuera de rango, es una alarma.

Las métricas de §6 y §7 no son estimaciones: se obtienen del mismo mecanismo de
instrumentación que produjo las mediciones de la fase 4.

## 9. Interfaz con los otros módulos

R1 escribe el rol en `metadata` en la **tabla 2** y usa prioridades **20000 a
29999**. Emite `host_autenticado` y `sesion_revocada`. Consume `ataque_detectado`
de R3 para revocar la sesión del atacante. Ver `../contratos/tablas-openflow.md`.

```
   R1 --host_autenticado--> R2 (conoce el rol para aplicar política)
   R1 --host_autenticado--> R3 (línea base de la terna IP/MAC/puerto)
   R3 --ataque_detectado--> R1 (revoca sesión) --sesion_revocada--> R2 (extiende bloqueo)
```

## 10. Métricas comprometidas

| Métrica | Objetivo (AVZ02) | Valor medido | Cómo se mide |
|---|---|---|---|
| Latencia de autenticación (p95) | ≤ 500 ms | **1.45 ms** @100/s; < 2 ms hasta 4 000/s *(medido)* | `tools/bench_packetin.py`, fase 4 |
| CPU del controlador @100 flujos/s | ≤ 60 % | **4 %** *(medido)* | `/proc/self/stat` en el banco |
| Logins concurrentes por segundo | — | **~4 000/s** operativo, **~11 000/s** techo *(medido)* | fase 4, rampa de carga |
| Tasa de bloqueo de accesos inválidos | ≥ 95 % *(objetivo)* | **Pendiente** | `tests/integration/`, requiere fase 5 |
| Roles y niveles jerárquicos soportados | 4 | 4 (§2) *(diseño)* | Codificación de `metadata`, contrato de tablas |

**Declaración honesta:** la tasa de bloqueo de accesos inválidos todavía **no está
medida**. Requiere el banco de ataques de la fase 5, bloqueado hasta instalar
herramientas en el host atacante. No se presenta ningún número para esa fila.
