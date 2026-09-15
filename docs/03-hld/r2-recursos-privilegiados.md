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

## 1. Inventario de recursos y criterio de clasificación [20]

Qué recursos existen en el campus y cuáles son privilegiados. La rúbrica evalúa
la precisión con que se identifican los recursos críticos.

| Recurso | Subred o IP | Clasificación | Roles con acceso | Grado de protección |
|---|---|---|---|---|
| Servidor de notas | | Crítico | Docente, superusuario | |
| Repositorio de exámenes | | Crítico | Docente, superusuario | |
| Servidor de laboratorio | | Intermedio | | |
| Portal académico | | General | Todos | |

## 2. Mecanismo de restricción y su justificación [20]

Por qué RBAC sobre políticas OpenFlow y no ACL estáticas, firewall tradicional o
ABAC. Comparación de alternativas.

## 3. Reglas de acceso: claridad y coherencia [20]

Cómo se expresa una política. Modelo de datos de la política de acceso, en
formato declarativo, que es lo que después se despliega como slice.

```yaml
# Ejemplo de slice predefinido para la demo del parcial
slice: laboratorio-redes
recursos:
  - nombre: servidor-notas
    destino: 172.16.0.10/32
    puertos: [443]
    roles_permitidos: [docente, superusuario]
  - nombre: repo-examenes
    destino: 172.16.0.20/32
    puertos: [22, 443]
    roles_permitidos: [superusuario]
politica_por_defecto: denegar
```

## 4. Coherencia con la arquitectura general [20]

Cómo encaja R2 en el pipeline. Usa la tabla 3 y los rangos de prioridad 30000 a
49999 según `../contratos/tablas-openflow.md`. Lee el rol desde `metadata`, que
escribe R1, y reacciona a los eventos `ataque_detectado` y `sesion_revocada` de R3.

## 5. Estimación de entradas de TCAM por switch [10]

La rúbrica pide de forma explícita el número máximo de entradas TCAM estimadas
en un switch. Desglose:

| Origen de la regla | Entradas estimadas | Justificación |
|---|---|---|
| Permisos por rol y recurso | | roles × recursos privilegiados |
| Denegaciones explícitas | | |
| Denegación por defecto | 1 | una entrada agregada, no una por host |
| **Total R2** | | |

Argumento clave: las reglas se agregan por subred de recurso y por rol, no por
host individual. Una regla por host haría crecer la tabla linealmente con la
población del campus, lo que es inviable en un switch real.

## 6. Eficiencia y carga sobre el controlador SDN [10]

Cuántos Packet-In genera R2 en régimen permanente. Las denegaciones se instalan
con timeout corto para registrar el intento sin acumular entradas permanentes,
como ya se definió en el caso de uso CU-02.

## 7. Métricas comprometidas

| Métrica | Objetivo | Cómo se mide |
|---|---|---|
| Precisión en la restricción | ≥ 95% de accesos no autorizados bloqueados | `tests/integration/` |
| Cobertura del inventario de recursos | | |
| Sesiones concurrentes soportadas | | |
| Sobrecarga: CPU, memoria, TCAM | CPU ≤ 60%, TCAM ≤ 50 | |

## 8. Caso de uso asociado

CU-02, ya especificado en el AVZ03. Referenciarlo, no repetirlo.
