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
#
# La fuente por defecto es Times New Roman (Windows/MiKTeX). Si tu equipo no
# la tiene instalada (p. ej. Linux sin fuentes de Microsoft), sobreescribe con:
#   MAINFONT="Liberation Serif" bash scripts/md-a-pdf.sh <entrada.md> <salida.pdf>
#
# Nota: NO se usa --number-sections a proposito. Los encabezados de los
# documentos ya traen su numero manual (1., 2., 3. ...) porque esos numeros
# mapean a los criterios de la rubrica; activar la numeracion automatica
# produciria titulos duplicados del tipo "1.1 1. Planteamiento del problema".

set -euo pipefail
ENTRADA="${1:?Uso: bash scripts/md-a-pdf.sh <entrada.md> <salida.pdf>}"
SALIDA="${2:?Falta la ruta de salida}"
MAINFONT="${MAINFONT:-Times New Roman}"

mkdir -p "$(dirname "$SALIDA")"

pandoc "$ENTRADA" \
  --from markdown+pipe_tables+yaml_metadata_block \
  --resource-path="$(dirname "$ENTRADA")" \
  --pdf-engine=xelatex \
  --toc --toc-depth=3 \
  -V lang=es \
  -V geometry:margin=2.5cm \
  -V mainfont="$MAINFONT" \
  -V fontsize=11pt \
  -V colorlinks=true \
  -V linkcolor=black \
  -M title="TEL354 - Redes Definidas por Software" \
  -M subtitle="Grupo 5" \
  -M date="$(date +%d/%m/%Y)" \
  -o "$SALIDA"

echo "Generado: $SALIDA"
