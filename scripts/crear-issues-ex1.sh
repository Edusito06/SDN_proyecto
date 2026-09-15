#!/usr/bin/env bash
# Convierte la rúbrica del Ex1 en issues de GitHub.
#
# Requisitos: GitHub CLI instalado y autenticado.
#   gh auth login
#
# Uso:
#   bash scripts/crear-issues-ex1.sh WillRider2003/RedesDefProyecto
#
# Idea: cada criterio de la rúbrica es un issue con su peso en el título. Así en
# cualquier momento se ve qué criterio está sin cubrir, que es la causa número uno
# de perder puntos en este tipo de proyecto.

set -euo pipefail
REPO="${1:?Uso: bash scripts/crear-issues-ex1.sh <owner/repo>}"
MS="Ex1-Parcial"

echo "Creando etiquetas..."
gh label create "R1"           --repo "$REPO" --color 1f77b4 --description "Control de acceso por rol"        --force
gh label create "R2"           --repo "$REPO" --color ff7f0e --description "Recursos privilegiados"           --force
gh label create "R3"           --repo "$REPO" --color d62728 --description "Ataques encubiertos"              --force
gh label create "arquitectura" --repo "$REPO" --color 9467bd --description "Arquitectura global"              --force
gh label create "docs"         --repo "$REPO" --color 7f7f7f --description "Documentación"                    --force
gh label create "codigo"       --repo "$REPO" --color 2ca02c --description "Implementación"                   --force
gh label create "pruebas"      --repo "$REPO" --color 8c564b --description "Plan de pruebas y métricas"       --force
gh label create "demo"         --repo "$REPO" --color e377c2 --description "Demo en vivo del parcial"         --force
gh label create "bloqueante"   --repo "$REPO" --color b60205 --description "Bloquea a otros trabajos"         --force

echo "Creando milestone..."
gh api "repos/$REPO/milestones" -f title="$MS" \
  -f description="Primera entrega calificada del proyecto. Arquitectura 40 pts + HLD 40 pts." \
  -f due_on="2026-10-16T05:00:00Z" >/dev/null 2>&1 || echo "  (el milestone ya existía)"

crear() {  # crear "titulo" "cuerpo" "etiquetas"
  gh issue create --repo "$REPO" --milestone "$MS" \
    --title "$1" --body "$2" --label "$3" >/dev/null
  echo "  + $1"
}

echo "Creando issues de arquitectura (40 pts)..."
crear "[ARQ 8] Elección de controlador fundamentada" \
  "Cerrar el ADR 0001 (Ryu/OVS vs P4/Tofino) y redactar la sección 2 de docs/02-arquitectura.md con la comparación de alternativas.

Bloquea a casi todo lo demás: hasta que no se decida el plano de datos, el HLD de R3 no se puede cerrar." \
  "arquitectura,docs,bloqueante"
crear "[ARQ 14] Módulos bien definidos y su interacción" \
  "Diagrama de módulos mostrando la interacción R1-R2-R3. Base: el contrato de eventos en docs/contratos/tablas-openflow.md." \
  "arquitectura,docs"
crear "[ARQ 14] Justificación de decisiones y trazabilidad a requerimientos" \
  "Tabla decisión-requerimiento-alternativa descartada-motivo. Sección 4 de docs/02-arquitectura.md." \
  "arquitectura,docs"
crear "[ARQ 14] Separación de planos, reutilización y escalabilidad" \
  "Sección 5 de docs/02-arquitectura.md." "arquitectura,docs"
crear "[ARQ 14] Uso creativo de SDN" \
  "Segmentación avanzada, políticas inteligentes, balanceo dinámico. Es donde se gana diferenciación frente a otros grupos. Sección 6." \
  "arquitectura,docs"
crear "[ARQ 4] Redundancia y tolerancia a fallos del plano de control" \
  "Qué pasa si cae Ryu. Modo failsecure vs failstandalone del OVS. Sección 7." "arquitectura,docs"
crear "[ARQ 2] Extensibilidad sin romper lo existente" "Sección 8." "arquitectura,docs"
crear "[INFRA] Secciones 9.1 a 9.8 de infraestructura" \
  "Integración con DHCP/DNS/autenticación [5], agregar switches [2], crecimiento de usuarios y VLANs [5], recuperación ante caída [2], enlaces redundantes [2], ubicación segura de servidores [5], minimización de recursos [4], monitoreo [5]." \
  "arquitectura,docs"
crear "[ARQ] Análisis cualitativo frente a los CINCO requerimientos" \
  "La rúbrica exige evaluar la arquitectura frente a R1..R5, no solo los tres del grupo. Una solución fuerte ante una amenaza pero vulnerable ante otras no se considera adecuada. Sección 10." \
  "arquitectura,docs"

echo "Creando issues de R1 (10 pts)..."
crear "[R1 16] Lógica de acceso y autenticación de usuarios válidos" \
  "Decidir: identificación por MAC (CU-01) o 802.1X con RADIUS. La MAC es suplantable y el jurado lo va a señalar." "R1,docs"
crear "[R1 16] Matriz de usuarios, niveles de acceso y permisos" \
  "Matriz rol x recurso completa, sin superposiciones ni vacíos." "R1,docs"
crear "[R1 16] Flujo desde solicitud hasta autorización" "Diagrama de secuencia basado en CU-01." "R1,docs"
crear "[R1 10] Pertinencia técnica del método de control" "RADIUS vs ACL vs RBAC vs políticas OpenFlow." "R1,docs"
crear "[R1 10] Escalabilidad en logins por segundo" \
  "Cuántas autenticaciones por segundo soporta el diseño y dónde está el cuello de botella." "R1,docs"
crear "[R1 11] Latencia con múltiples usuarios" "Latencia de autenticación en ms." "R1,docs"
crear "[R1 11] Supervisión del control de acceso" "Registro de eventos y endpoint de métricas." "R1,docs"
crear "[R1 10] Multiplataforma y portabilidad" "Qué tan atado queda al VNRT." "R1,docs"

echo "Creando issues de R2 (10 pts + código + demo)..."
crear "[R2 20] Inventario de recursos y criterio de clasificación" \
  "Tabla recurso-subred-clasificación-roles-grado de protección." "R2,docs"
crear "[R2 20] Justificación del mecanismo de restricción" "RBAC sobre OpenFlow vs ACL vs firewall vs ABAC." "R2,docs"
crear "[R2 20] Reglas de acceso claras y coherentes" "Modelo declarativo del slice en YAML." "R2,docs"
crear "[R2 20] Coherencia con la arquitectura general" "Encaje en tabla 3 y prioridades 30000-49999." "R2,docs"
crear "[R2 10] Estimación de entradas TCAM por switch" \
  "La rúbrica lo pide de forma explícita y casi nadie lo hace. Desglose por origen de regla, con el argumento de agregación por subred y rol en vez de por host." \
  "R2,docs"
crear "[R2 10] Eficiencia y carga sobre el controlador" "Packet-In en régimen permanente." "R2,docs"
crear "[R2] CÓDIGO: motor de políticas y despliegue de slice" \
  "Entregable 4 del Ex1: se entrega el código, con énfasis en el de R2." "R2,codigo,bloqueante"
crear "[R2] DEMO: despliegue de slice predefinido en vivo" \
  "Entregable 5 del Ex1, durante el examen parcial. Necesita topología scriptada y ensayo previo. NO dejar para la última semana." \
  "R2,demo,bloqueante"

echo "Creando issues de R3 (20 pts)..."
crear "[R3 10] Definición y delimitación de la amenaza" \
  "Network scanning, port scanning, IP spoofing, muchos a uno. Por qué son encubiertos." "R3,docs"
crear "[R3 12] Diseño lógico del mecanismo de detección" \
  "Formalizar ventana T, umbrales N_dst, N_port, N_miss. Decidir si umbrales fijos o detección de anomalías." "R3,docs"
crear "[R3 12] Diseño del proceso de mitigación" "Escalera de respuesta: rate limit, drop, revocación." "R3,docs"
crear "[R3 12] Identificación de patrones anómalos en la intranet" \
  "Qué firma en el tráfico distingue un escaneo de un uso legítimo intenso." "R3,docs"
crear "[R3 12] Mecanismos de detección: IDS, anomalías, políticas de flujo" \
  "Definir cuál mecanismo se usa para cada vector de ataque." "R3,docs"
crear "[R3 8] Análisis del entorno afectado y alcance" "Frontera con R5." "R3,docs"
crear "[R3 8] Capacidad de detección temprana" \
  "Detectar en los primeros Packet-In del host sospechoso, antes de que el escaneo sea efectivo." "R3,docs"
crear "[R3 8] Variedad de ataques y fracción de tráfico malicioso que pasa" \
  "Cuántos vectores distintos cubre la solución y cuánto se escapa." "R3,docs"
crear "[R3 8] Flexibilidad y escalabilidad del diseño" "Cómo añadir un vector nuevo sin rehacer el módulo." "R3,docs"
crear "[R3 4] Justificación tecnológica de herramientas" \
  "Por qué estas herramientas y no otras." "R3,docs"
crear "[R3 3] Tiempo estimado de detección" "Sustentar el compromiso de 500 ms del AVZ02." "R3,docs,pruebas"
crear "[R3 3] Tiempo estimado de mitigación" \
  "Desde la detección hasta que la regla está instalada y filtrando." "R3,docs,pruebas"
crear "[R3] Documentación de respuesta a incidentes" \
  "Cómo se registra, notifica y evalúa un incidente. La rúbrica lo pide y suele olvidarse." "R3,docs"

echo "Creando issues transversales..."
crear "[INFRA] Scriptear la topología del laboratorio" \
  "Convertir el armado manual de namespaces, veth y bridges OVS del Lab 1 en topology/campus_topo.py. Sin esto la demo del parcial depende del estado de una máquina." \
  "codigo,bloqueante"
crear "[PRUEBAS] Banco de medición de KPIs" \
  "Scripts que generen los ataques (nmap para escaneo, hping3 para spoofing y flood) y midan detección, tiempo y falsos positivos. La diferencia entre 'estimamos 500 ms' y 'medimos 480 ms sobre 50 corridas' es grande en la nota." \
  "pruebas,codigo"
crear "[DOCS 15] Orden y organización del documento" "Formato, numeración, índice, figuras referenciadas." "docs"
crear "[DOCS 20] Desarrollo de los temas requeridos" "Revisión final contra la rúbrica completa." "docs"
crear "[PRES 20] Evidencia de trabajo coordinado y validación con el coach" \
  "Peso 20 en la rúbrica. Se cubre con el historial de PRs, las actas de las asesorías dominicales y los avances semanales." "docs"
crear "[PRES 15] Manejo de expositores y formalidad" "Ensayo de la presentación." "docs"
crear "[PRES 15] Uso adecuado de herramientas multimedia" \
  "Diagramas legibles, sin capturas de pantalla ilegibles ni texto diminuto." "docs"
crear "[PRES 15] Definición del scope del proyecto" \
  "Dejar claro en la presentación qué entra y qué no entra en la solución." "docs"
crear "[ADMIN] Consultar al coach las inconsistencias del enunciado" \
  "1) El enunciado de entregables habla de HLD de R1B, R1C, R2 y R5 (incluido R0 primera parte), nomenclatura que no existe en el resto del documento y no calza con R1/R2/R3 de G5.
2) G5 figura con 5 integrantes cuando el enunciado fija un máximo de 4.
3) Confirmar si el VNRT expone algún switch programable o bmv2, para cerrar el ADR 0001." \
  "bloqueante"

echo
echo "Listo. Revisa el tablero en: https://github.com/$REPO/issues?q=is%3Aopen+milestone%3A$MS"
