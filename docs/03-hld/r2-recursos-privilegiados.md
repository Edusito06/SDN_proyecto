# HLD R2 — Restricción de acceso a recursos privilegiados

> Vale **10 puntos** del Ex1. Es además el requerimiento cuyo **código se entrega**
> y cuya **demo en vivo** se hace durante el parcial: despliegue de un slice
> predefinido. Es el que más hay que tener andando, no solo escrito.
>
> El HLD es diseño conceptual, no de software. El nivel de detalle debe permitir
> que un ingeniero competente derive un diseño concreto. El detalle de
> implementación va en el LLSD.
>
> Los números entre corchetes son los pesos de la rúbrica del Ex1.
>
> **Convención:** *medido* = dato reproducible de `../lab/resultados-vnrt.md`.
> *objetivo* = compromiso del AVZ02 aún sin verificar. *analítico* = cálculo sobre
> un modelo, no una medición.

## 1. Inventario de recursos y criterio de clasificación [20]

### Criterio de clasificación

Un recurso se clasifica por el **daño que causa su compromiso**, no por dónde
está alojado:

| Clase | Criterio | Política por defecto |
|---|---|---|
| **Crítico** | Su alteración o filtración compromete la integridad académica o datos personales | Denegar salvo rol explícitamente autorizado |
| **Intermedio** | Su caída interrumpe la operación docente, pero no compromete integridad | Permitir a roles autenticados, registrar acceso |
| **General** | Servicio de consumo masivo sin datos sensibles | Permitir a todo host autenticado |

### Inventario instanciado en el VNRT

El VNRT no trae servidores dedicados: son cuatro hosts (`h1`-`h4`). Para que el
diseño sea **demostrable**, dos de ellos cumplen el papel de recursos protegidos.
La elección no es arbitraria: `h3` y `h4` cuelgan de **sw3**, mientras los
clientes `h1` y `h2` cuelgan de **sw2**, de modo que **todo acceso a un recurso
privilegiado cruza el enlace hacia sw1**, que es el switch central y el punto
natural donde aplicar la política.

| Recurso | Papel | IP (plano de datos) | Switch / puerto OF | Puertos | Clasificación | Roles con acceso |
|---|---|---|---|---|---|---|
| **Servidor de notas** | `h3` | `10.0.0.3/32` | sw3 / puerto 2 (`ens5`) | 443 | **Crítico** | Docente, Superusuario |
| **Repositorio de exámenes** | `h4` | `10.0.0.4/32` | sw3 / puerto 1 (`ens6`) | 22, 443 | **Crítico** | Superusuario |
| Cliente docente/alumno | `h1` | `10.0.0.1/32` | sw2 / puerto 2 (`ens5`) | — | General | — (origen) |
| Cliente alumno | `h2` | `10.0.0.2/32` | sw2 / puerto 3 (`ens6`) | — | General | — (origen) |

Mapeo puerto a puerto **verificado experimentalmente** en la fase 1 del
reconocimiento (correlación de contadores de tráfico), no tomado del diagrama.

### Correspondencia con un campus real

Lo instanciado en el laboratorio representa esta clasificación de campus, que es
la que se defiende ante el jurado:

| Recurso de campus | Clase | Instanciado como |
|---|---|---|
| Servidor de notas / actas | Crítico | `h3` |
| Repositorio de exámenes | Crítico | `h4` |
| Sistema de matrícula | Crítico | *(mismo patrón, no instanciado)* |
| Servidores de laboratorio | Intermedio | *(mismo patrón)* |
| Portal académico, DNS, DHCP | General | tráfico no privilegiado |

## 2. Mecanismo de restricción y su justificación [20]

**Se adopta RBAC aplicado como políticas OpenFlow en la tabla 3**, leyendo el rol
desde `metadata` que escribe R1.

| Alternativa | Qué ofrece | Por qué se descarta |
|---|---|---|
| **ACL estáticas por IP** | Sin controlador, soportado por cualquier switch | La regla se ata a la IP del cliente. Con DHCP la IP cambia y la política se rompe. No expresa *rol*, y no reacciona a eventos de R3 |
| **Firewall tradicional perimetral** | Maduro, inspección profunda | Es un punto único en el borde: **no ve el tráfico intra-campus**, que es justo la amenaza (un alumno dentro de la intranet accediendo a notas). Desviarlo todo al firewall crea cuello de botella y tromboning |
| **ABAC** (atributos: hora, ubicación, postura) | Máxima expresividad | Complejidad de evaluación y de prueba desproporcionada para 4 roles. Evolución del Ex2 |
| **RBAC sobre OpenFlow** ← *adoptado* | El rol viaja en `metadata`; la decisión se aplica distribuida, en cada switch, a velocidad de línea | — |

Razones decisivas:

1. **Aplica donde ocurre la amenaza.** La política vive en el switch de acceso,
   así que un alumno que intenta alcanzar el servidor de notas se bloquea en el
   primer salto, sin atravesar la red. Un firewall perimetral no vería ese
   tráfico.
2. **Desacopla identidad de dirección.** La regla matchea el **rol** en
   `metadata`, no la IP del cliente. Un docente conserva su permiso aunque cambie
   de IP, y el número de reglas no crece con la población (§5).
3. **Es reactivo por diseño.** Consume `ataque_detectado` y `sesion_revocada` de
   R1/R3 y extiende el bloqueo sin esperar un nuevo `Packet-In`, tal como
   especifica el flujo alternativo del CU-02.
4. **Está verificado que el entorno lo soporta:** la fase 2 confirmó
   `write_metadata`, `goto_table`, meters y grupos sobre OVS 3.3.9.

## 3. Reglas de acceso: claridad y coherencia [20]

### Modelo declarativo de política (lo que se despliega como slice)

```yaml
# Slice de la demo del parcial. IPs reales del plano de datos del VNRT.
slice: campus-recursos-privilegiados
version: 1
politica_por_defecto: denegar

recursos:
  - nombre: servidor-notas
    destino: 10.0.0.3/32
    ubicacion: { dpid: sw3, puerto_of: 2 }
    puertos: [443]
    roles_permitidos: [docente, superusuario]

  - nombre: repo-examenes
    destino: 10.0.0.4/32
    ubicacion: { dpid: sw3, puerto_of: 1 }
    puertos: [22, 443]
    roles_permitidos: [superusuario]

registro:
  denegaciones: true
  timeout_regla_denegacion_s: 10
```

### Traducción a reglas OpenFlow

Cada entrada del YAML se compila a reglas de la **tabla 3**, dentro de los rangos
del contrato: **30000-39999 permisos**, **40000-49999 denegaciones**.

| # | Prioridad | Match | Acción | Origen |
|---|---|---|---|---|
| 1 | 39000 | `metadata rol=2 (docente)`, `ipv4_dst=10.0.0.3`, `tcp_dst=443` | `goto_table:4` | permiso notas/docente |
| 2 | 39000 | `metadata rol=4 (superusuario)`, `ipv4_dst=10.0.0.3`, `tcp_dst=443` | `goto_table:4` | permiso notas/superusuario |
| 3 | 39000 | `metadata rol=4`, `ipv4_dst=10.0.0.4`, `tcp_dst=22` | `goto_table:4` | permiso repo/ssh |
| 4 | 39000 | `metadata rol=4`, `ipv4_dst=10.0.0.4`, `tcp_dst=443` | `goto_table:4` | permiso repo/https |
| 5 | 41000 | `ipv4_dst=10.0.0.3` | `drop` + registrar | denegación explícita notas |
| 6 | 41000 | `ipv4_dst=10.0.0.4` | `drop` + registrar | denegación explícita repo |
| 7 | 30000 | *(sin match de recurso)* | `goto_table:4` | tráfico general |

**Coherencia garantizada por construcción:** los permisos (prioridad más alta que
las denegaciones dentro de su propósito) se evalúan primero; lo que no coincide
con ningún permiso cae en la denegación explícita del recurso. **No hay solapes
ni vacíos**: todo paquete dirigido a un recurso privilegiado termina en la regla 1-4
(permitido) o en la 5-6 (denegado). El tráfico que no va a un recurso privilegiado
pasa por la regla 7.

### Ciclo de vida de una denegación

La regla de denegación se instala con `hard_timeout` corto (10 s) en lugar de ser
permanente. El propósito es doble: **registrar el intento** y **no acumular
entradas**. El efecto secundario deseado es que un atacante insistente vuelve a
generar `Packet-In` al expirar la regla, lo que alimenta a R3 con la señal de un
patrón de acceso repetido.

## 4. Coherencia con la arquitectura general [20]

R2 ocupa la **tabla 3** y los rangos **30000-49999**, según
`../contratos/tablas-openflow.md`. Lee el rol desde `metadata` (escrito por R1 en
la tabla 2) y nunca lo modifica.

```
 tabla 0 (R3)      tabla 1 (R3)      tabla 2 (R1)        tabla 3 (R2)       tabla 4
 antispoofing  ->  mitigación   ->   identidad y rol  -> política recurso -> reenvío
 IP+MAC+puerto     bloqueo activo    write_metadata      lee metadata        L2
      |                 |                  |                   |
   descarta          descarta         Packet-In si         drop + registro
   spoofing          atacante         no conoce            si no autorizado
```

Por qué el orden importa para R2:

- R2 **nunca ve** tráfico de un host ya marcado como atacante: la tabla 1 lo cortó
  antes. Esto evita gastar evaluación de política en tráfico que ya está condenado.
- R2 **siempre** encuentra el rol en `metadata`: si R1 no lo hubiera escrito, el
  paquete no habría llegado a la tabla 3. La dependencia es explícita y unidireccional.

Eventos:

| R2 consume | De | Efecto |
|---|---|---|
| `host_autenticado` | R1 | Conoce la asociación host↔rol |
| `sesion_revocada` | R1 | Retira permisos del host sin esperar Packet-In |
| `ataque_detectado` | R3 | Propaga el bloqueo del atacante al resto de switches |

| R2 emite | Hacia | Carga útil |
|---|---|---|
| `acceso_denegado` | R3 | MAC origen, IP destino, recurso |

## 5. Estimación de entradas de TCAM por switch [10]

> **Advertencia conceptual obligatoria:** OVS es un switch por software y **no
> tiene TCAM**; usa tabla de flujos en memoria más caché de megaflows en kernel.
> Todo lo de esta sección es un **cálculo analítico sobre un modelo de switch de
> hardware**, presentado por separado de cualquier medición hecha en OVS. Las
> cifras medidas en el laboratorio están al final de la sección, claramente
> diferenciadas.

### Fórmula

Para R2, el número de entradas por switch es:

```
E_R2  =  Σ (puertos_r × roles_permitidos_r)  +  N_recursos  +  1
          r ∈ recursos                          (deny/recurso)  (deny por defecto)
```

Lo esencial: **E_R2 depende de recursos × roles, no del número de usuarios.**

### Desglose para el inventario del laboratorio

| Origen de la regla | Entradas | Justificación |
|---|---|---|
| Permisos por rol y recurso | **4** | notas:443 × {docente, superusuario} = 2; repo:{22,443} × {superusuario} = 2 |
| Denegaciones explícitas | **2** | una por recurso protegido |
| Denegación por defecto | **1** | entrada agregada, no una por host |
| **Total R2** | **7** | |

### Proyección a escala de campus

| Escenario | Recursos | Puertos/recurso | Roles permitidos | E_R2 |
|---|---|---|---|---|
| Laboratorio (actual) | 2 | ~1.5 | ~1.5 | **7** |
| Campus moderado | 20 | 2 | 2 | **101** |
| Campus grande | 50 | 3 | 3 | **501** |

**El argumento clave de la rúbrica:** las reglas se agregan por recurso y por rol,
no por host. Un diseño que instalara una regla por usuario daría, en un campus de
10 000 usuarios, del orden de 10 000 entradas solo para R2 — inviable en hardware
real, donde una TCAM típica ronda las 2 000-8 000 entradas. Con agregación por
rol, 20 recursos protegidos caben en ~101 entradas: **dos órdenes de magnitud
menos, y constante frente al crecimiento de la matrícula.**

### Presupuesto total por switch (analítico, modelo de hardware)

| Módulo | Entradas | Crece con |
|---|---|---|
| R1 (identidad) | 1 por host activo en ese switch | usuarios conectados **a ese switch** (acotado por nº de puertos) |
| R2 (política) | 7 (lab) / ~101 (campus) | recursos × roles |
| R3 (mitigación) | **≤ 50** *(compromiso AVZ02)*, con `idle`/`hard_timeout` | atacantes activos, autolimitado |
| Reenvío L2 | 1 por MAC aprendida | hosts activos |

### Contraste con lo medido en OVS (no es TCAM)

La fase 2 midió el comportamiento real del prototipo: OVS instaló **50 000 reglas
sin rechazar ninguna**, a un costo **plano de ~140 µs por regla** (sin degradación
entre N=5 000 y N=50 000). Es decir: **en el prototipo no hay problema de
capacidad de tabla**, ni de lejos. Esa holgura **no sustituye** el cálculo
analítico de arriba, porque un switch de hardware sí tiene un tope duro que OVS no
tiene. Presentarlas juntas sería un error conceptual; por eso van separadas.

## 6. Eficiencia y carga sobre el controlador SDN [10]

### Régimen permanente

R2 genera `Packet-In` **solo** en el primer contacto de un host con un recurso
privilegiado, o al reintentar tras expirar una denegación. En régimen permanente
el tráfico autorizado se conmuta en el switch (regla en tabla 3 → `goto_table:4`)
sin tocar el controlador.

Estimación para un campus moderado: 200 docentes acceden al servidor de notas una
vez por hora de clase → **≈ 0.06 Packet-In/s**. Frente al techo operativo medido
de ~4 000 eventos/s, la carga de R2 en régimen permanente es **despreciable**.

### Peor caso: intentos de acceso no autorizados repetidos

Es el caso que sí acota el diseño. Con `hard_timeout = 10 s` en la denegación, un
host insistente puede generar como máximo **1 Packet-In cada 10 s por cada par
(host, recurso)**, porque mientras la regla vive el tráfico se descarta en el
switch sin subir. Un atacante que rotara entre 100 recursos generaría ~10
Packet-In/s: sigue siendo tres órdenes de magnitud por debajo del techo.

### Capacidad medida del controlador (fase 4)

| Carga | Eventos procesados | CPU | p95 latencia |
|---|---|---|---|
| 100 /s | 100 /s | 4 % | 1.45 ms |
| 1 000 /s | 1 000 /s | 32-34 % | ~1.5 ms |
| 4 000 /s | 4 000 /s | 53-67 % | ~1.6 ms |
| saturación | **~11 000 /s (techo)** | ~110 % | **> 4 s** |

**Conclusión:** el presupuesto de control de R2 es holgadísimo. El riesgo real no
es la carga legítima de R2, sino un **flood deliberado** que empuje al controlador
a saturación (donde el p95 se dispara a segundos). La defensa correcta no es del
plano de control: es aplicar **meters** —confirmados soportados en la fase 2— para
limitar la tasa en el plano de datos antes de que el controlador se ahogue. Esto
conecta directamente con la escalera de mitigación de R3.

## 7. Métricas comprometidas

| Métrica | Objetivo (AVZ02) | Estado | Cómo se mide |
|---|---|---|---|
| Precisión en la restricción | ≥ 95 % de accesos no autorizados bloqueados | **Pendiente de medir** | `tests/integration/`, requiere el banco de la fase 5 |
| Cobertura del inventario de recursos | 100 % de recursos críticos con política explícita | **2/2 en el laboratorio** *(diseño)* | Revisión del slice contra el inventario de §1 |
| Sesiones concurrentes soportadas | — | **~4 000/s** operativo, **~11 000/s** techo *(medido)* | fase 4 |
| CPU del controlador | ≤ 60 % | **4 %** @100 eventos/s *(medido)* | fase 4 |
| Entradas TCAM | ≤ 50 | **7** para el inventario actual *(analítico)* | §5, cálculo sobre modelo de hardware |

**Declaración honesta:** la precisión de restricción (≥ 95 %) es el compromiso
central de R2 y **todavía no está medida**. Depende de la fase 5, hoy bloqueada
por falta de herramientas en el host atacante. No se presenta ningún número
estimado en su lugar.

## 8. Caso de uso asociado

CU-02, especificado en el AVZ03. Se mantiene íntegro; la única corrección es de
direccionamiento: donde el CU-02 habla de "la subred de recursos privilegiados",
se instancia como `10.0.0.3/32` y `10.0.0.4/32` en el plano de datos
`10.0.0.0/24` (el AVZ03 asumía `192.168.0.0/24`, que el reconocimiento identificó
como red de **gestión**, no de usuario).

## 9. Demo del parcial: qué se muestra en vivo

Guion propuesto para el despliegue del slice, con el resultado observable:

| Paso | Acción | Resultado esperado |
|---|---|---|
| 1 | Desplegar el slice vía Northbound API | Reglas 1-7 instaladas en tabla 3, verificable con `dump-flows` |
| 2 | Desde `h1` con rol **docente** → `10.0.0.3:443` | **Permitido.** Acierta regla 1 |
| 3 | Desde `h2` con rol **alumno** → `10.0.0.3:443` | **Denegado.** Acierta regla 5, se registra el intento |
| 4 | Desde `h2` con rol **alumno** → `10.0.0.4:22` | **Denegado.** Acierta regla 6 |
| 5 | Mostrar `dump-flows` | Ninguna regla fuera del rango 30000-49999 |
| 6 | Reintentar el paso 3 antes de 10 s | Descartado en el switch, **sin** nuevo Packet-In |

El paso 5 es el que demuestra ante el jurado que el contrato de tablas se cumple,
y el 6 el que demuestra el control de carga sobre el controlador.
