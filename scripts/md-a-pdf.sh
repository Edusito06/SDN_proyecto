#!/usr/bin/env bash
# Exporta un documento Markdown a PDF con formato de entrega.
#
# Requiere pandoc y una distribución de LaTeX.
#   Windows:  winget install --id JohnMacFarlane.Pandoc -e
#             winget install --id MiKTeX.MiKTeX -e
#   Linux:    sudo apt install pandoc texlive-xetex texlive-lang-spanish
#
# Uso:
#   bash scripts/md-a-pdf.sh docs/02-arquitectura.md entregables/ex1/Arquitectura-G5.pdf

set -euo pipefail
ENTRADA="${1:?Uso: bash scripts/md-a-pdf.sh <entrada.md> <salida.pdf>}"
SALIDA="${2:?Falta la ruta de salida}"

mkdir -p "$(dirname "$SALIDA")"

pandoc "$ENTRADA" \
  --from markdown+pipe_tables+yaml_metadata_block \
  --pdf-engine=xelatex \
  --toc --toc-depth=3 \
  --number-sections \
  -V lang=es \
  -V geometry:margin=2.5cm \
  -V mainfont="Times New Roman" \
  -V fontsize=11pt \
  -V colorlinks=true \
  -V linkcolor=black \
  -M title="TEL354 - Redes Definidas por Software" \
  -M subtitle="Grupo 5" \
  -M date="$(date +%d/%m/%Y)" \
  -o "$SALIDA"

echo "Generado: $SALIDA"
