# HLD R1 — Control de acceso a la red según rol

> Vale **10 puntos** del Ex1. Se expone en clase el jueves 17 de setiembre junto
> con R2, 15 minutos, y esa exposición cuenta como nota del laboratorio de la
> semana 5.
>
> Los números entre corchetes son los pesos de la rúbrica del Ex1.

## 1. Lógica de acceso y autenticación de usuarios válidos [16]

Cómo se identifica a un usuario y cómo se le asigna un rol. Decisión pendiente y
que conviene cerrar antes del jueves: identificación por MAC, que es lo que
describe el CU-01, o autenticación real con 802.1X y RADIUS.

La identificación por MAC es simple y demostrable, pero es suplantable, y el
jurado lo va a señalar. Vale la pena anticiparse: o se justifica como decisión de
alcance para el laboratorio, o se diseña 802.1X y se implementa la versión simple.

## 2. Definición de usuarios, niveles de acceso y permisos [16]

| Rol | Nivel | Permisos | Recursos accesibles |
|---|---|---|---|
| Alumno | Mínimo | | Recursos académicos básicos |
| Docente | Medio | | Plataformas de evaluación |
| Administrador de red | Alto | Define y ajusta políticas, revoca sesiones | |
| Superusuario | Máximo | | Todos |

La rúbrica valora que no haya superposiciones ni vacíos entre roles. Conviene una
matriz rol por recurso completa, sin celdas ambiguas.

## 3. Pertinencia técnica del método de control [10]

RADIUS, ACL, RBAC o políticas OpenFlow. Justificar la elección frente a las demás.

## 4. Lógica del proceso desde solicitud hasta autorización [16]

Diagrama de secuencia. El flujo base ya está en el CU-01: primer paquete,
Packet-In, consulta de la tabla de roles, FLOW_MOD, reenvío en hardware.

## 5. Multiplataforma y portabilidad [10]

Qué tan atado queda el diseño al VNRT y qué haría falta para llevarlo a hardware.

## 6. Escalabilidad: logins por segundo [10]

Cuántas autenticaciones por segundo soporta el diseño y dónde está el cuello de
botella.

## 7. Latencia con múltiples usuarios [11]

Latencia de autenticación en milisegundos y cómo se mantiene baja. El costo está
en el primer paquete de cada flujo, que sí sube al controlador.

## 8. Supervisión del correcto funcionamiento [11]

Cómo se monitorea y audita el control de acceso. Registro de eventos, endpoint de
métricas en la Northbound API.

## 9. Interfaz con los otros módulos

R1 escribe el rol en `metadata` en la tabla 2 y usa prioridades 20000 a 29999.
Emite `host_autenticado` y `sesion_revocada`. Consume `ataque_detectado` de R3
para revocar la sesión del atacante. Ver `../contratos/tablas-openflow.md`.

## 10. Métricas comprometidas

| Métrica | Objetivo | Cómo se mide |
|---|---|---|
| Tasa de bloqueo de accesos inválidos | | |
| Latencia de autenticación | | |
| Roles y niveles jerárquicos soportados | | |
| Logins concurrentes por segundo | | |
