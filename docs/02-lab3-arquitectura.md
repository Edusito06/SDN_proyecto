# Documento de Arquitectura de la Solución — Laboratorio 3

> **Qué es este documento y por qué es distinto de `02-arquitectura.md`.** Este
> archivo sigue la estructura de 13 secciones que exige
> `TEL354_LAB3_PLANTILLA-ARQUITECTURA_2026-2.docx` para el segundo entregable
> del Laboratorio 3 (Presentación + Documento de Arquitectura + Anexos, 5 pts).
> `docs/02-arquitectura.md` sigue la rúbrica del Ex1 (12 criterios, 40 pts) y
> es un documento distinto, con otra estructura y otro momento de entrega
> (semana del Ex1, octubre). Ambos documentos beben de las mismas fuentes —
> los HLD, el ADR, el contrato de tablas, los resultados del VNRT — pero no se
> deben fusionar: cada uno responde a la rúbrica que le corresponde.
>
> **Convención de datos:** *(medido)* = experimental y reproducible, con su
> comando. *(objetivo)* = compromiso del AVZ02, sin verificar aún. *(analítico)*
> = cálculo derivado de datos medidos. *(estimado)* = valor de dimensionamiento
> sin medición, marcado como tal según pide la guía para la sección 7 en esta
> etapa.
>
> **Marcadores pendientes de este borrador**, señalados donde aparecen: la
> fecha y horario exactos de entrega, la bitácora real de asesorías con el
> coach, y la confirmación del equipo sobre la asignación de secciones en 0.1.
> Son datos que solo el equipo puede completar; no se inventan aquí.

## 0. Portada y control de versiones

**Laboratorio N°:** 3 — **Tema:** Arquitectura del Proyecto — **Semestre:** 2026-2
**Curso:** TEL354 — Redes Definidas por Software — **Grupo:** 5
**Profesor:** Christian Quispe — **Coach:** Fernando Guzmán (asesoría domingos 5 PM)
**Horario de laboratorio:** *(pendiente de confirmar — falta el código, p. ej. H089X)*

### 0.1 Integrantes y roles

Roles base, de `README.md`. La columna de secciones responsables es una
**propuesta de reparto**, a confirmar con el equipo antes de entregar.

| Código | Apellidos y nombres | Rol en el equipo | Secciones propuestas |
|---|---|---|---|
| 20221862 | Antaurco Corsino, Willian | Líder / Gestor | 0, 1, 12 |
| 20192676 | Cuadros David, Jairo Leonardo | Investigador | 3, 4 |
| 20207779 | Mauricio Cristóbal, Eva María | Testeador / QA | 10, 11 |
| 20213805 | Gutiérrez Hurtado, Jeanpier Gustavo | Codificador | 5, 6 |
| 20227163 | Rodas Arias, Eduardo | Arquitecto de solución | 2, 7, 8, 9 |

### 0.2 Historial de versiones

| Versión | Fecha | Autor | Cambios respecto de la versión anterior |
|---|---|---|---|
| 0.1 | 27 ago – 3 set | Equipo | AVZ01-03: rol de integrantes, concepto de operación, casos de uso CU-01/CU-02 |
| 0.2 | 15 set | Eduardo (asistido por Claude Code) | ADR 0001 cerrado con datos del reconocimiento VNRT (fases 1 y 3); habilitado OpenFlow 1.3; HLD de R1 y R2 con datos medidos (fases 2 y 4) |
| 0.3 | 17-21 set | Eduardo (asistido por Claude Code) | Migración Ryu → os-ken documentada (Ryu no instala en Python 3.12); banco de ataques ejecutado, 5 de 6 escenarios (Fase 5) |
| 0.4 | 22 set | Eduardo (asistido por Claude Code) | HLD de R3 completado con umbrales de detección calculados sobre datos medidos; primera versión de este documento |

### 0.3 Índice, índice de figuras e índice de tablas

Se genera de forma automática al exportar a PDF (`scripts/md-a-pdf.sh`).

## 1. Contexto y alcance

### Necesidad de negocio

La universidad necesita que **solo sus usuarios** (alumnos, profesores,
administrativos) usen los recursos de la red del campus, para reducir el
costo de tráfico IP no autorizado y el riesgo de acceso indebido a sistemas
internos — notas, matrícula, repositorios académicos — desde dentro de la
propia intranet, que es tráfico que **nunca pasa por el firewall
perimetral** y por eso ningún control de borde lo ve.

### Alcance de esta solución

| Dentro del alcance | Fuera del alcance |
|---|---|
| Control de acceso por rol en la red cableada de acceso (**R1**) | Red inalámbrica, con su propio controlador |
| Autorización a recursos privilegiados sobre tráfico intra-campus (**R2**) | Protección perimetral contra ataques externos (**R5**, no asignado a G5) |
| Detección y mitigación de escaneo, spoofing y flood dentro de la intranet (**R3**, específico de G5) | Mitigación de DDoS volumétrico coordinado desde fuera (**R4**, no asignado) |
| Registro de intentos de acceso y de incidentes, expuesto por API REST | Gestión del ciclo de vida de cuentas de usuario (altas/bajas administrativas) |

### Supuestos

- El VNRT (Open vSwitch 3.3.9 + OpenFlow 1.3, controlador os-ken) es el banco
  de validación, no el diseño. El diseño es para una red de campus genérica;
  ver `docs/03-hld/*` para la declaración explícita en cada HLD.
- La identidad de R1 se resuelve hoy por MAC + puerto de ingreso, no por
  credenciales criptográficas (declarado como decisión de alcance, HLD R1 §3).
- El controlador es una única instancia para la maqueta del curso (ver §9).

### Glosario mínimo

SDN (Software-Defined Networking), plano de control/plano de datos, OpenFlow
1.3, `metadata` (registro de 64 bits que viaja entre tablas del pipeline),
Packet-In (evento que un switch eleva al controlador cuando no sabe qué hacer
con un paquete), RBAC (control de acceso basado en rol), TCAM (memoria
asociativa de contenido, donde un switch de hardware guarda sus reglas de
reenvío — OVS, por ser software, no la tiene).

## 2. Requerimientos

### 2.1 Requerimientos del proyecto

| ID | Enunciado | Tipo | Prioridad | Asignado a G5 |
|---|---|---|---|---|
| R1 | Controlar el acceso a la red de los usuarios válidos, acorde con su rol | Funcional | Alta | Base |
| R2 | Restringir el acceso a recursos privilegiados solo a usuarios autorizados | Funcional | Alta | Base |
| R3 | Detectar y mitigar ataques encubiertos en la intranet (network scanning, port scanning, IP spoofing, muchos-a-uno) | Funcional | Alta | **Específico, vale el doble** |
| R4 | Detectar y mitigar ataques DDoS de fuerza bruta en la intranet | Funcional | — | No asignado |
| R5 | Proteger la red de ataques externos | Funcional | — | No asignado |

### 2.2 Ficha de especificación

#### R1 — Control de acceso por rol

| Campo | Contenido |
|---|---|
| Identificador | R1 |
| Enunciado | El sistema debe permitir el acceso a la red del campus únicamente a usuarios registrados, y aplicarles el conjunto de permisos que corresponde a su rol |
| Tipo | Funcional |
| Prioridad y justificación | Alta. Es la puerta de entrada de toda la solución: si R1 no funciona, R2 no tiene identidad sobre la que aplicar políticas |
| Actores | Alumno, docente, administrador de red, superusuario |
| Precondiciones | El host está físicamente conectado a un switch de acceso con sesión OpenFlow 1.3 activa hacia el controlador |
| Criterios de aceptación | CA1. Dado un host con MAC registrada, cuando emite su primer paquete, entonces obtiene exactamente los permisos de su rol. CA2. Dado un host con MAC no registrada, cuando se conecta, entonces recibe el rol mínimo (alumno) y el evento queda auditado |
| Métricas y valores objetivo | Latencia de autenticación p95 ≤ 500 ms (**1.45 ms medido** a 100 logins/s); 4 roles soportados; logins concurrentes: **~4 000/s operativo, ~11 000/s techo** *(medido)* |
| Restricciones técnicas | OpenFlow 1.3, soporte de `write_metadata` y `goto_table` (**confirmados**, fase 2) |
| Vínculo con seguridad | Es la base de identidad de la que depende R2, y la primera línea que R3 puede revocar ante un ataque confirmado |

#### R2 — Restricción a recursos privilegiados

| Campo | Contenido |
|---|---|
| Identificador | R2 |
| Enunciado | El sistema debe restringir el acceso a recursos privilegiados del campus solo a los roles autorizados, incluido el tráfico que nunca cruza el perímetro |
| Tipo | Funcional |
| Prioridad y justificación | Alta. Cierra el hueco que ningún firewall perimetral ve: acceso indebido origen-intranet a destino-intranet |
| Actores | Docente, administrador de red, superusuario (como sujetos con acceso); alumno (como sujeto denegado por defecto) |
| Precondiciones | R1 ya escribió el rol del host en `metadata` |
| Criterios de aceptación | CA1. Dado un usuario con rol autorizado, cuando accede a un recurso crítico, entonces el tráfico se permite en el primer salto. CA2. Dado un usuario sin rol autorizado, cuando lo intenta, entonces se descarta y el intento queda registrado con timeout de 10 s |
| Métricas y valores objetivo | Precisión de restricción ≥ 95 % *(objetivo, pendiente de medir contra implementación real)*; entradas de TCAM ≤ 50 (**10 calculado** para el inventario propuesto, analítico) |
| Restricciones técnicas | Rangos de prioridad 30000-49999 del contrato de tablas; recursos críticos agrupados en subred de servidores |
| Vínculo con seguridad | Retroalimenta a R3: una denegación repetida es señal temprana de reconocimiento (`acceso_denegado`) |

#### R3 — Detección y mitigación de ataques encubiertos (específico de G5)

| Campo | Contenido |
|---|---|
| Identificador | R3 |
| Enunciado | El sistema debe detectar y mitigar network scanning, port scanning, IP spoofing y tráfico de muchos-a-uno dentro de la intranet, con tiempo de detección acotado |
| Tipo | Funcional |
| Prioridad y justificación | Alta, vale el doble de R1/R2 en la rúbrica. Sin R3 el resto de la solución no cubre la amenaza que motiva el proyecto (mitigar ataques encubiertos) |
| Actores | Atacante interno (host comprometido o malicioso dentro del campus), administrador de red (revisa incidentes) |
| Precondiciones | R1 ha aprendido la terna (IP, MAC, puerto) legítima de cada host, para que la tabla 0 tenga contra qué contrastar |
| Criterios de aceptación | CA1. Dado un host que escanea más de N_port=15 puertos distintos en T=2 s, entonces se activa el nivel 1 de mitigación antes de 500 ms (**~115 ms medido/analítico**). CA2. Dado un paquete con terna IP/MAC/puerto inconsistente, entonces se descarta en el primer paquete |
| Métricas y valores objetivo | Tasa de detección ≥ 95 % *(objetivo, diseño calibrado, pendiente contra implementación real)*; falsos positivos ≤ 2 % *(pendiente)*; tiempo de detección ≤ 500 ms (**115-297 ms medido/analítico** en 3 de 4 vectores, pendiente el escaneo lento) |
| Restricciones técnicas | Tablas 0 y 1, prioridades 50000-59999; *meters* de OpenFlow confirmados soportados (fase 2) |
| Vínculo con seguridad | Es el requerimiento de seguridad central del grupo; retroalimenta a R1 (revocación de sesión) y R2 (propagación de bloqueo) |

### 2.3 Priorización

1. **R1** — bloquea todo lo demás; sin identidad no hay política ni contexto para detectar ataques con terna conocida.
2. **R2** — depende de R1, pero es desarrollable en paralelo una vez fijado el contrato de `metadata`.
3. **R3** — depende de R1 para la terna legítima, pero su detección estructural (spoofing) y estadística (scan/flood) no dependen de que R2 exista; es el de mayor riesgo si no se atiende, porque vale el doble y es el diferenciador del grupo frente al jurado.
4. **R4 y R5** — no asignados; el riesgo de dejarlos sin diseño es bajo para la nota de G5, pero la arquitectura debe declarar cómo los acomodaría (§8.4).

## 3. Atributos de calidad

Escenarios en el formato de seis partes que pide la guía, con datos medidos
donde ya existen.

| Atributo | Fuente | Estímulo | Artefacto | Entorno | Respuesta | Medida |
|---|---|---|---|---|---|---|
| **Escalabilidad** | Alumnado del campus al inicio de clases | Ráfaga de autenticaciones (R1) | Controlador SDN (os-ken) | Operación normal, hora punta | Todas las solicitudes se procesan y se instala la regla del rol | p95 de latencia < 500 ms hasta 4 000 logins/s; techo en 11 000/s *(medido, Fase 4)* |
| **Seguridad** | Host dentro de la intranet ejecutando un port scan | Cientos de intentos de conexión a puertos distintos de un mismo destino | Contador estadístico de R3 en el controlador | Operación normal, ataque activo | Se activa el nivel 1 de mitigación antes de cruzar la ventana T | Tiempo de detección ≤ 500 ms (**~115 ms** medido/analítico) |
| **Fiabilidad / Disponibilidad** | El controlador único de la maqueta se cae o pierde el canal OpenFlow | Pérdida de conexión switch↔controlador | Switches OVS en `fail_mode=secure` | Falla del plano de control | El switch deja de instalar reglas nuevas pero conserva las ya instaladas; ningún host nuevo se autentica hasta reconectar | Tiempo de reconexión no medido en esta etapa; declarado como limitación de instancia única (§9) |

## 4. Decisiones de arquitectura

### AD-01. Controlador y plano de datos

| Campo | Contenido |
|---|---|
| Estado | Aceptada (`docs/adr/0001-controlador-y-plano-de-datos.md`) |
| Contexto | El AVZ01 planteaba P4 sobre Intel Tofino; AVZ02 y AVZ03 describían Ryu sobre OVS. Había que cerrar la ambigüedad con datos del entorno real |
| Alternativas consideradas | A. Controlador Python (Ryu/os-ken) sobre Open vSwitch con OpenFlow 1.3. B. P4 sobre Intel Tofino |
| Decisión | Se elige A |
| Justificación | Es una decisión forzada por los datos: el reconocimiento del VNRT no encontró ningún componente de la cadena P4 (ni `p4c`, ni `bmv2`, ni rastro de Tofino) en ninguno de los 8 nodos *(medido, fase 3)*, mientras que Open vSwitch 3.3.9 ya estaba desplegado y solo requería habilitar OpenFlow 1.3 |
| Consecuencias positivas | Se apoya en infraestructura ya disponible; permite llegar a la demo en vivo del Ex1 |
| Consecuencias negativas | Se pierde la flexibilidad de un plano de datos programable a nivel de paquete, que P4 sí ofrecería para R3 |

**Matriz de decisión ponderada de AD-01.** Escala de 1 a 5, donde 5 es mejor.

| Atributo de calidad | Peso | A. Ryu/os-ken sobre OVS | B. P4 sobre Tofino | Sustento |
|---|---|---|---|---|
| Disponibilidad en el entorno VNRT | 40 % | 5 | 1 | OVS 3.3.9 ya desplegado; ningún componente P4 encontrado *(medido)* |
| Tiempo hasta tener algo operativo para el Ex1 | 25 % | 5 | 1 | Solo faltaba habilitar OF1.3 por bridge; P4 requeriría aprovisionar toolchain completo |
| Alineación con lo que enseña el curso | 15 % | 5 | 3 | Los laboratorios del curso son sobre OpenFlow/OVS |
| Madurez y documentación del ecosistema | 10 % | 4 | 3 | os-ken es fork activo de Ryu; P4/Tofino tiene curva de aprendizaje mayor |
| Flexibilidad futura (programabilidad de paquete) | 10 % | 3 | 5 | P4 permitiría lógica de detección en el propio plano de datos |
| **Puntaje ponderado** | 100 % | **4.70** | **1.90** | Se elige A. Se pierde flexibilidad futura, evaluado y aceptado |

### AD-02. Mecanismo de identidad para R1

| Campo | Contenido |
|---|---|
| Estado | Aceptada (`docs/03-hld/r1-control-acceso.md` §3, §5) |
| Contexto | R1 necesita identificar el host antes de asignarle rol, en un entorno de laboratorio con 4 hosts y plazo acotado |
| Alternativas consideradas | A. Identidad por MAC + puerto de ingreso, contrastada en el controlador. B. 802.1X con RADIUS y suplicante en el terminal |
| Decisión | Se elige A para el Ex1; B queda documentada como evolución para el Ex2 |
| Justificación | El costo de desplegar suplicantes y un servidor RADIUS no es sostenible en el plazo, y la debilidad de A (MAC falsificable) queda cubierta por la tabla 0 de R3, que de todos modos hay que construir |

**Matriz de decisión ponderada de AD-02.**

| Atributo de calidad | Peso | A. MAC + puerto | B. 802.1X / RADIUS | Sustento |
|---|---|---|---|---|
| Velocidad de implementación para el Ex1 | 30 % | 5 | 2 | A no requiere infraestructura nueva; B necesita servidor RADIUS y suplicantes configurados |
| Complejidad de despliegue en el VNRT | 25 % | 5 | 2 | 4 hosts de laboratorio, sin gestión de dispositivos personal |
| Integración con R3 (antispoofing) | 20 % | 5 | 3 | La validación IP+MAC+puerto de R3 sale gratis para A, que ya la necesita |
| Robustez de la identidad | 15 % | 2 | 5 | La MAC es falsificable; 802.1X autentica criptográficamente |
| Costo de infraestructura adicional | 10 % | 5 | 2 | A no añade componentes; B requiere un servidor RADIUS nuevo |
| **Puntaje ponderado** | 100 % | **4.55** | **2.65** | Se elige A. Se pierde robustez de identidad, mitigada por R3 (tabla 0) |

### AD-03. Mecanismo de restricción para R2

| Campo | Contenido |
|---|---|
| Estado | Aceptada (`docs/03-hld/r2-recursos-privilegiados.md` §3) |
| Contexto | R2 necesita bloquear acceso indebido a recursos críticos, incluido tráfico que nunca pasa por el borde de la red |
| Alternativas consideradas | A. RBAC aplicado como políticas OpenFlow, leyendo el rol de `metadata`. B. Firewall perimetral |
| Decisión | Se elige A |
| Justificación | Un firewall perimetral no ve tráfico intra-campus, que es exactamente la amenaza que R2 debe cerrar; desviar todo el tráfico interno al perímetro crearía además un cuello de botella (*tromboning*) |

**Matriz de decisión ponderada de AD-03.**

| Atributo de calidad | Peso | A. RBAC sobre OpenFlow | B. Firewall perimetral | Sustento |
|---|---|---|---|---|
| Visibilidad de tráfico intra-campus | 35 % | 5 | 1 | El firewall solo ve tráfico que cruza el borde; el acceso indebido interno nunca llega a él |
| Desacople de la IP del cliente | 25 % | 5 | 3 | La regla de A coincide con el rol en `metadata`, no con la IP, que cambia con DHCP |
| Reactividad ante eventos de R3 | 20 % | 4 | 2 | A consume `ataque_detectado`/`sesion_revocada` directamente; un firewall externo necesitaría integración adicional |
| Escalabilidad de reglas | 20 % | 4 | 3 | En A las reglas se agregan por rol × recurso, no por host (HLD R2 §6) |
| **Puntaje ponderado** | 100 % | **4.60** | **2.10** | Se elige A |

### AD-04. Umbrales fijos vs. detección basada en aprendizaje para R3

Decisión documentada en `docs/03-hld/r3-ataques-encubiertos.md` §3, sin matriz
ponderada propia porque la comparación no es entre dos alternativas
mutuamente excluyentes en este momento, sino entre adoptar una técnica ahora
o declararla evolución futura. Se adoptan **umbrales fijos** para el Ex1: la
separación medida entre tráfico legítimo y ataque ya es de dos a cuatro
órdenes de magnitud (HLD R3 §11), y no hay datos suficientes (seis corridas
puntuales) para entrenar ni validar un modelo con rigor. ML queda como
evolución explícita para el Ex2.

## 5. Vista de componentes

### 5.1 Diagrama de arquitectura

*(Pendiente: diagrama consolidado de los módulos de R1+R2+R3 dentro del
controlador. Existen hoy diagramas por módulo — `docs/diagramas/r1-modelo-red.pdf`,
`r1-secuencia-autenticacion.pdf`, `r1-interfaz-modulos.pdf`, `r2-pipeline-tablas.pdf`
— y el mapa de topología textual en `docs/diagramas/topologia-vnrt.md`. Falta
un diagrama único que muestre los tres módulos dentro del mismo controlador,
con el bus de eventos entre ellos. Se puede generar en la siguiente iteración.)*

El pipeline de tablas (que sí está diagramado, `r2-pipeline-tablas.pdf`) es la
columna vertebral de esta vista: cada módulo vive en una o más tablas
concretas del mismo switch, no en un servidor aparte.

### 5.2 Catálogo de módulos

| ID | Módulo | Responsabilidad principal | Ubicación | Req. | Estado |
|---|---|---|---|---|---|
| M01 | Antispoofing estructural | Contrasta IP+MAC+puerto contra lo aprendido; descarta discrepancias | Controlador + tabla 0 del switch | R3 | Diseñado |
| M02 | Mitigación activa | Instala y retira reglas de la escalera de 3 niveles (meter, drop, revocación) | Controlador + tabla 1 del switch | R3 | Diseñado |
| M03 | Identidad y rol | Identifica el host por MAC, escribe el rol en `metadata` | Controlador + tabla 2 del switch | R1 | Diseñado, HLD completo |
| M04 | Política de recursos | Lee el rol de `metadata`, decide acceso a recursos privilegiados | Controlador + tabla 3 del switch | R2 | Diseñado, HLD completo |
| M05 | Reenvío común | Conmutación L2 aprendida | Controlador + tabla 4 del switch | Todos | Validado en el banco (`tools/bench_ataques.py`) |
| M06 | Bus de eventos interno | Publica/consume `host_autenticado`, `sesion_revocada`, `acceso_denegado`, `ataque_detectado`, `mitigacion_aplicada` | Proceso del controlador | R1, R2, R3 | Contrato definido (`docs/contratos/tablas-openflow.md`) |
| M07 | Northbound API REST | Expone estado y métricas de cada módulo; permite revocación/liberación manual | Controlador | R1, R2, R3 | Endpoints definidos por HLD, sin implementar |

Ningún módulo queda fuera de la matriz de trazabilidad (§10) y ningún
módulo de la matriz queda sin fila aquí.

### 5.3 Patrones aplicados

| Patrón | Dónde se aplica | Qué problema resuelve | Contraindicación asumida |
|---|---|---|---|
| **Message-queueing** | Bus de eventos interno (M06) entre R1, R2 y R3 | Permite que los tres módulos se desarrollen y prueben aislados: ninguno llama directamente al otro, solo publica y consume eventos | Añade una capa de indirección: depurar un flujo completo (spoofing → revocación → propagación) exige rastrear varios eventos en vez de una sola llamada |
| **Capas** | Separación control/datos propia de SDN, y dentro del controlador, separación por tabla (0-1 R3, 2 R1, 3 R2, 4 común) | Cada módulo razona sobre su propia tabla sin conocer la lógica interna de las otras — es lo que permite el contrato de prioridades | Una decisión que necesita información de una capa distinta (p. ej. R3 necesitando el rol de R1) debe pasar por el bus de eventos, no acceder directo, lo que agrega latencia mínima pero real |

## 6. Vista de interfaces

| ID | Origen | Destino | Protocolo y puerto | Datos | Modo | Seguridad |
|---|---|---|---|---|---|---|
| I01 | Host de la red de acceso | Switch SDN | Ethernet/ARP/DHCP, capa 2 | Primer paquete de presentación en la red | Asíncrono | Ninguna a este nivel; la validación ocurre en I02 |
| I02 | Switch SDN | Controlador (os-ken) | OpenFlow 1.3, 6653/TCP | `packet_in`, `flow_mod`, `packet_out` | Asíncrono | Por definir — el VNRT no exige TLS en el canal de control hoy |
| I03 | Controlador | Administrador de red / herramientas de operación | REST sobre HTTPS, puerto por definir | Métricas, incidentes, revocación manual | Síncrono | Por definir |
| I04 | M03 (R1) ↔ M04 (R2) ↔ M01/M02 (R3) | Entre sí, vía M06 | Bus de eventos interno (en proceso, no de red) | `host_autenticado`, `sesion_revocada`, `acceso_denegado`, `ataque_detectado`, `mitigacion_aplicada` | Asíncrono | No aplica (interno al proceso del controlador) |

**Observación honesta:** I02 e I03 tienen su protocolo de transporte
declarado pero **no** su capa de seguridad (TLS/autenticación de la API). Es
el mismo tipo de hueco que la propia plantilla del laboratorio señala como
error típico si se deja sin declarar — queda anotado aquí en vez de
inventado, para cerrarlo antes de la siguiente entrega.

## 7. Vista de despliegue

### Bosquejo de infraestructura (validado en el VNRT)

```
                    Controlador os-ken (192.168.0.10:6653)
                                    │  canal OpenFlow (red de gestión)
                                   sw1  (switch central, dpid a223f2c04547)
                              ┌────┴────┐
                             sw2        sw3
                          ┌───┴───┐  ┌───┴───┐
                         h1      h2  h3      h4
                    (cliente)(cliente)(notas)(exámenes)
```

Fuente: `docs/diagramas/topologia-vnrt.md`, verificado por correlación de
contadores de tráfico *(medido, fase 1)*.

### Inventario de elementos y versiones

| Elemento | Tecnología | Versión | Nota |
|---|---|---|---|
| Controlador | os-ken (fork mantenido de Ryu) | 4.2.2, en `venv` | Ryu no instala en Python 3.12 (`AttributeError` en `setup.py`) |
| Switches | Open vSwitch | 3.3.9 | 3 bridges, OpenFlow 1.3 habilitado |
| Sistema operativo (todos los nodos) | Ubuntu | 24.04 LTS | Kernel 6.8.0-138/139-generic |
| Python (controlador) | CPython | 3.12.3 | — |
| Northbound API | REST (por implementar) | — | Endpoints definidos en cada HLD, sin código aún |

### Direccionamiento y dimensionamiento *(estimado, se refina en la semana de topología)*

| Red | Función | En el VNRT | Estimado para un campus real |
|---|---|---|---|
| Plano de datos | Tráfico de usuario | `10.0.0.0/24` (4 hosts) | Varias `/22` o `/23` por facultad, según AVZ02 *(estimado)* |
| Gestión | Canal OpenFlow + SSH | `192.168.0.0/24` | Red de gestión dedicada, fuera de alcance de este documento |
| Recursos críticos | Servidores privilegiados | `h3`, `h4` en `sw3` (banco de prueba) | Subred de servidores dedicada, `10.20.0.0/24` propuesto en HLD R2 |

**Recursos asignados por nodo:** 2 vCPU / 1.9 GiB en el controlador (único
nodo con el doble de cómputo de la topología), 1 vCPU / 961 MiB en cada
switch y host *(medido, fase 1)*. El controlador es, por diseño de la
plataforma de laboratorio, el nodo con más margen — consistente con ser el
componente que más CPU consume bajo carga (§9).

## 8. High Level Design por requerimiento

### 8.1 R1 — Control de acceso a la red por rol

Desarrollado en detalle en `docs/03-hld/r1-control-acceso.md`. Resumen: identidad
por MAC + puerto de ingreso (AD-02), rol escrito en `metadata`, cuatro roles
jerárquicos sin superposición, latencia de autenticación de **1.45 ms** a 100
logins/s y techo de **~11 000/s** *(medido)*.

### 8.2 R2 — Restricción a recursos privilegiados

Desarrollado en detalle en `docs/03-hld/r2-recursos-privilegiados.md`. Resumen:
RBAC sobre OpenFlow (AD-03), políticas expresadas como *slice* declarativo,
presupuesto de TCAM de **10 entradas** para el inventario propuesto,
proyectado a **~101** para un campus moderado (20 recursos críticos)
*(analítico)*.

### 8.3 R3 — Detección y mitigación de ataques encubiertos (requerimiento específico)

Desarrollado en detalle en `docs/03-hld/r3-ataques-encubiertos.md`, completado
en esta misma iteración. Resumen: detección estructural (spoofing, tabla 0) y
estadística (scan/flood, contador en el controlador con ventana T=2s),
umbrales N_dst=20, N_port=15, N_miss=20 calibrados sobre las seis corridas de
la Fase 5, escalera de mitigación de 3 niveles, tiempos de detección entre
**~14.5 ms y ~297 ms** según el vector *(medido/analítico)*, muy por debajo
del compromiso de 500 ms — con la excepción declarada del escaneo lento
(`-T1`), aún sin cerrar.

### 8.4 Requerimientos no asignados

| Req. | Enfoque propuesto | Por qué la arquitectura lo soportaría | Brecha conocida |
|---|---|---|---|
| R4 (DDoS de fuerza bruta) | Extender el mismo contador estadístico de R3 (M01/M02) con un umbral de tasa agregada por destino, en vez de por origen | El bus de eventos y la escalera de mitigación ya generalizan a "un contador más, un umbral más" (HLD R3 §10) | No hay módulo dedicado ni umbral definido; requeriría distinguir tráfico distribuido de un único atacante |
| R5 (protección perimetral) | Un firewall o IDS en el borde, fuera del pipeline de OpenFlow, que solo reenvíe al controlador tráfico ya admitido | La arquitectura ya separa explícitamente "intranet" (R3) de "perímetro" (R5) en el alcance (§1); no hay conflicto de responsabilidad | Ningún componente de borde está diseñado; es una integración completamente nueva |

## 9. Modelo de control

**Para la maqueta del curso se adopta un controlador único (os-ken)**, y se
declara como limitación conocida — la misma categoría que la guía ubica junto
a Floodlight/Ryu en instancia única. Es una elección de alcance, no un
descuido: el VNRT tiene 3 switches y 4 hosts, y el techo medido (~11 000
Packet-In/s idealizado, ~1 300-1 400/s parseando cada paquete como hará R3 en
la práctica — Fase 4 y Fase 5, escenario 5) está muy por encima de lo que esta
topología genera.

**Para un despliegue real de campus**, la vía de evolución es un **clúster de
varias instancias con consenso Raft**, siguiendo el modelo de ONOS (Tabla 4.3
de la guía del laboratorio): un almacén distribuido para el estado fuerte
(identidad, sesiones activas) y *gossip* para el estado que tolera
desactualización (métricas, contadores de R3 no críticos).

**Trade-off de consistencia vs. disponibilidad (CAP), ante una partición:**
se elige **negar el acceso antes que concederlo**. Si dos instancias del
controlador discreparan sobre el rol de un usuario, o si el servidor que
resuelve la identidad no respondiera, el host se queda en cuarentena — la
misma decisión que ya está declarada en el HLD de R1 (§3): "el costo de dejar
entrar a un equipo no identificado es mayor que el de dejar sin red a un
usuario legítimo durante la caída". Es consistente con la postura de R3: ante
la duda, contener primero, y dejar la reversión de un falso positivo a una
decisión posterior del administrador (escalera de nivel 3).

**Primer componente en saturarse al crecer el campus:** el propio
controlador, y específicamente el hilo único que procesa eventos —
`os-ken`/`eventlet` es monohilo; en saturación un núcleo llega al 100 % de
uso mientras el segundo vCPU del nodo queda ocioso *(medido, Fase 4)*. La vía
de crecimiento no es una máquina más grande, es repartir switches entre varias
instancias de controlador — el mismo argumento que sostiene la migración al
modelo de clúster de este apartado.

## 10. Matriz de trazabilidad

| Req. | Criterio | Módulos | Interfaces | Decisión | Medida de verificación |
|---|---|---|---|---|---|
| R1 | CA1 | M03, M05, M06 | I01, I02, I04 | AD-02 | 100 % de reglas instaladas coinciden con el rol *(pendiente contra implementación real)* |
| R1 | CA2 | M03, M06 | I02, I04 | AD-02 | Tasa de bloqueo de accesos inválidos ≥ 95 % *(pendiente)* |
| R2 | CA1 | M04, M06 | I02, I04 | AD-03 | Acceso permitido en primer salto, verificado con `dump-flows` |
| R2 | CA2 | M04, M06 | I02, I04 | AD-03 | Precisión de restricción ≥ 95 % *(pendiente)* |
| R3 | CA1 (scan) | M01, M02, M06 | I02, I04 | AD-01, AD-04 | Tiempo de detección ≤ 500 ms (**115-297 ms medido/analítico**) |
| R3 | CA2 (spoofing) | M01, M06 | I02, I04 | AD-01 | Detección en el primer paquete (**~1.45 ms medido**) |
| R4 | Sin definir | Ninguno (extensión propuesta en §8.4) | Ninguna | Ninguna | Sin definir |
| R5 | Sin definir | Ninguno (fuera de alcance, §1) | Ninguna | Ninguna | Sin definir |

**Lectura honesta:** R1 y R2 tienen módulo, interfaz y decisión, pero sus
criterios de aceptación cuantitativos (≥95 %) siguen pendientes porque
dependen de código que aún no existe (`src/` vacío). R3 es el único
requerimiento con tiempos ya medidos o calculados sobre datos medidos, gracias
al banco de ataques de la Fase 5. R4 y R5 quedan deliberadamente sin fila, tal
como advierte la propia plantilla: así se ve, sin disimularlo, dónde no llega
todavía el diseño.

## 11. Riesgos y limitaciones conocidas

| Riesgo o limitación | Origen | Plan de mitigación / estado |
|---|---|---|
| Identidad por MAC es falsificable | AD-02 | Cubierto por la tabla 0 de R3 (terna IP+MAC+puerto); evolución a 802.1X declarada para el Ex2 |
| Controlador único es punto único de falla | §9 | Declarado como limitación conocida de la maqueta; vía de evolución a clúster con Raft descrita |
| El canal OpenFlow (I02) y la API REST (I03) no tienen capa de seguridad definida | §6 | Anotado como "por definir", no como hueco silencioso; se cierra antes de la siguiente entrega |
| Escenario de escaneo lento (`-T1`) sin cerrar | HLD R3 §3, §6 | Puede obligar a bajar los umbrales N_dst/N_port o alargar la ventana T; pendiente de cerrar la corrida en el VNRT |
| Tasa de detección (≥95 %) y falsos positivos (≤2 %) de R3, y precisión de restricción de R2, aún no medidos contra código real | `src/` vacío | Requiere implementar los módulos y repetir el banco de ataques contra la implementación, no solo contra el banco de aprendizaje L2 usado en la Fase 5 |
| No se pudo determinar el emparejamiento exacto de puertos sw1↔sw2 y sw1↔sw3 | Reconocimiento VNRT, fase 1 | No bloquea el diseño (la topología en estrella ya está confirmada); se resolvería con descubrimiento LLDP |
| El VNRT es un entorno compartido del curso que puede reaprovisionarse | Regla 7 de `CLAUDE.md` | El venv de os-ken y los scripts de banco quedan documentados para poder recrearse si el entorno cambia |

## 12. Bitácora de retroalimentación

*(Pendiente de completar con el equipo — no se inventa contenido aquí. Si ya
hubo alguna asesoría con el coach o retroalimentación en clase, se completa
esta tabla con lo que realmente se dijo, antes de exportar a PDF.)*

| N | Fuente | Observación recibida | Cambio aplicado | Sección | Estado |
|---|---|---|---|---|---|
| — | — | *(sin asesorías registradas aún)* | — | — | — |

### 12.1 Registro de asesorías con el coach

| Fecha | Duración | Temas tratados | Acuerdos |
|---|---|---|---|
| *(pendiente)* | | | |

## Anexos

### Anexo A — Fuentes consultadas

1. N. McKeown et al., "OpenFlow: Enabling Innovation in Campus Networks," *ACM Computer Commun. Review*, vol. 38, no. 2, 2008, pp. 69–74.
2. S. Sharma, D. Staessens, D. Colle, M. Pickavet, P. Demeester, "In-Band Control, Queuing, and Failure Recovery Functionalities for OpenFlow," *IEEE Network*, vol. 30, no. 1, enero-febrero 2016, pp. 106–112.
3. Especificaciones OpenFlow, Open Networking Foundation, https://www.opennetworking.org/sdn-resources/onf-specifications
4. Documentación de Open vSwitch, https://www.openvswitch.org
5. os-ken (fork mantenido de Ryu), documentación del paquete y código fuente, PyPI.
6. G. Cuba, J. M. Becerra, Tesis PUCPLight — arquitectura de solución PUCPLight, PUCP (referencia de patrón de arquitectura, vía guía del Laboratorio 3).
7. Reconocimiento propio del entorno VNRT y banco de ataques del grupo: `docs/lab/resultados-vnrt.md` (fuente primaria de todos los datos *(medido)* de este documento).

### Anexo B — Declaración de uso de IA generativa

Se usó **Claude Code** (Anthropic) como asistente durante el reconocimiento
del entorno VNRT (fases 1 a 5), la redacción de los HLD de R1, R2 y R3, la
generación de diagramas de apoyo, y el armado de este documento de
arquitectura. El uso fue supervisado en cada paso por el arquitecto de
solución del equipo (Eduardo Rodas Arias): las decisiones de diseño, la
autorización de cada cambio de escritura sobre el VNRT, y la validación de
que ningún dato se presentara como medido sin serlo, fueron responsabilidad
humana. Los datos experimentales de este documento provienen de comandos
reales ejecutados contra el entorno de laboratorio, no de una fuente
generada; están todos trazados a `docs/lab/resultados-vnrt.md` con el
comando que los produjo.
