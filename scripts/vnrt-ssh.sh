#!/usr/bin/env bash
# Helper para conectarse a los nodos del VNRT sin recordar puertos.
#
# El gateway cambia entre sesiones del VNRT. Definilo antes de usar:
#   export VNRT_GW=10.20.12.153
#
# Uso:
#   scripts/vnrt-ssh.sh sw1 'ovs-vsctl show'   # corre el comando y vuelve
#   scripts/vnrt-ssh.sh h2                       # sesion interactiva
#   scripts/vnrt-ssh.sh                          # lista los nodos y sus puertos

set -euo pipefail

GW="${VNRT_GW:-}"
USER_SSH="${VNRT_USER:-ubuntu}"

declare -A PUERTO=(
  [controller]=5800
  [sw1]=5801  [sw2]=5802  [sw3]=5803
  [h1]=5811   [h2]=5812   [h3]=5813  [h4]=5814
)

if [ $# -eq 0 ]; then
  echo "Nodos disponibles (puerto):"
  for n in controller sw1 sw2 sw3 h1 h2 h3 h4; do
    printf "  %-11s %s\n" "$n" "${PUERTO[$n]}"
  done
  echo
  echo "Gateway actual: ${GW:-<sin definir, exporta VNRT_GW>}"
  echo "Ejemplo: VNRT_GW=10.20.12.153 scripts/vnrt-ssh.sh sw1 'ovs-vsctl show'"
  exit 0
fi

NODO="$1"; shift || true

if [ -z "${PUERTO[$NODO]:-}" ]; then
  echo "Nodo desconocido: $NODO. Usa uno de: ${!PUERTO[*]}" >&2
  exit 1
fi
if [ -z "$GW" ]; then
  echo "Falta el gateway. Exporta VNRT_GW con la IP vigente del VNRT." >&2
  exit 1
fi

P="${PUERTO[$NODO]}"
if [ $# -gt 0 ]; then
  ssh -o StrictHostKeyChecking=accept-new "$USER_SSH@$GW" -p "$P" "$@"
else
  ssh -o StrictHostKeyChecking=accept-new "$USER_SSH@$GW" -p "$P"
fi
