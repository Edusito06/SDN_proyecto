#!/usr/bin/env python3
"""Exporta un documento Markdown a PDF sin necesidad de pandoc ni LaTeX.

Alternativa a scripts/md-a-pdf.sh para maquinas donde no hay instalada una
distribucion de LaTeX. Solo requiere reportlab:

    python -m pip install reportlab fonttools

Uso:
    python scripts/md-a-pdf.py docs/03-hld/r1-control-acceso.md entregables/ex1/HLD-R1-G5.pdf

Soporta: encabezados, parrafos, negrita/cursiva/codigo en linea, listas,
citas, tablas de tuberias y bloques de codigo (los diagramas ASCII se
renderizan en monoespaciada y se reduce el cuerpo si la linea es muy ancha).
"""

import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

FONTS = "C:/Windows/Fonts"
BODY, BODY_B, BODY_I = "Body", "Body-Bold", "Body-Italic"
MONO, MONO_B = "Mono", "Mono-Bold"

# Caracteres sin glifo garantizado en las fuentes elegidas -> equivalente seguro.
SUSTITUCIONES = {
    "\u2714": "Si", "\u2718": "No", "\u2713": "Si", "\u2717": "No",
    "\u00a0": " ", "\u2011": "-", "\u2212": "-",
}


def registrar_fuentes():
    pdfmetrics.registerFont(TTFont(BODY, f"{FONTS}/arial.ttf"))
    pdfmetrics.registerFont(TTFont(BODY_B, f"{FONTS}/arialbd.ttf"))
    pdfmetrics.registerFont(TTFont(BODY_I, f"{FONTS}/ariali.ttf"))
    pdfmetrics.registerFont(TTFont(MONO, f"{FONTS}/consola.ttf"))
    pdfmetrics.registerFont(TTFont(MONO_B, f"{FONTS}/consolab.ttf"))
    pdfmetrics.registerFontFamily(BODY, normal=BODY, bold=BODY_B, italic=BODY_I)


def glifos_disponibles(ruta):
    from fontTools.ttLib import TTFont as FTFont
    f = FTFont(ruta)
    cubiertos = set()
    for tabla in f["cmap"].tables:
        cubiertos.update(tabla.cmap.keys())
    return cubiertos


def avisar_glifos_faltantes(texto_cuerpo, texto_codigo):
    """Evita que reportlab dibuje cuadros negros silenciosamente."""
    faltan = []
    for etiqueta, texto, ruta in (
        ("cuerpo", texto_cuerpo, f"{FONTS}/arial.ttf"),
        ("codigo", texto_codigo, f"{FONTS}/consola.ttf"),
    ):
        cubiertos = glifos_disponibles(ruta)
        ausentes = {c for c in set(texto) if ord(c) not in cubiertos and c not in "\n\r\t"}
        if ausentes:
            faltan.append((etiqueta, sorted(ausentes)))
    for etiqueta, chars in faltan:
        detalle = ", ".join(f"{c!r}(U+{ord(c):04X})" for c in chars)
        print(f"  AVISO: sin glifo en {etiqueta}: {detalle}", file=sys.stderr)
    return not faltan


def estilos():
    hojas = getSampleStyleSheet()
    s = {}
    s["h1"] = ParagraphStyle("h1", parent=hojas["Title"], fontName=BODY_B,
                             fontSize=18, leading=22, spaceAfter=14,
                             alignment=0, textColor=colors.HexColor("#1a3a5c"))
    s["h2"] = ParagraphStyle("h2", fontName=BODY_B, fontSize=13.5, leading=17,
                             spaceBefore=16, spaceAfter=7,
                             textColor=colors.HexColor("#1a3a5c"))
    s["h3"] = ParagraphStyle("h3", fontName=BODY_B, fontSize=11.5, leading=14,
                             spaceBefore=11, spaceAfter=5,
                             textColor=colors.HexColor("#33566f"))
    s["p"] = ParagraphStyle("p", fontName=BODY, fontSize=9.5, leading=13.5,
                            spaceAfter=7, alignment=TA_JUSTIFY)
    s["li"] = ParagraphStyle("li", parent=s["p"], leftIndent=14,
                             bulletIndent=4, spaceAfter=3.5)
    s["quote"] = ParagraphStyle("quote", parent=s["p"], leftIndent=10,
                                rightIndent=8, fontSize=9, leading=12.5,
                                textColor=colors.HexColor("#444444"),
                                borderPadding=(6, 6, 6, 8),
                                backColor=colors.HexColor("#f2f5f8"))
    s["celda"] = ParagraphStyle("celda", fontName=BODY, fontSize=8, leading=10.5)
    s["celda_h"] = ParagraphStyle("celda_h", fontName=BODY_B, fontSize=8,
                                  leading=10.5, textColor=colors.white)
    return s


def inline(texto):
    """Markdown en linea -> marcado de reportlab. Escapa XML primero."""
    t = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"`([^`]+)`",
               rf'<font face="{MONO}" size="8.5" color="#a03030">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)  # enlaces -> solo el texto
    return t


def fila_tabla(linea):
    partes = linea.strip().strip("|").split("|")
    return [p.strip() for p in partes]


def es_separador(linea):
    return bool(re.match(r"^\s*\|[\s:|-]+\|\s*$", linea))


def construir_tabla(filas, s, ancho_util):
    encabezado, cuerpo = filas[0], filas[1:]
    ncol = len(encabezado)

    # Ancho proporcional al contenido, con minimo y maximo razonables.
    pesos = []
    for i in range(ncol):
        largos = [len(encabezado[i])] + [len(f[i]) if i < len(f) else 0 for f in cuerpo]
        pesos.append(max(6, min(sum(largos) / max(1, len(largos)) + 4, 60)))
    total = sum(pesos)
    anchos = [ancho_util * p / total for p in pesos]

    datos = [[Paragraph(inline(c), s["celda_h"]) for c in encabezado]]
    for f in cuerpo:
        f = (f + [""] * ncol)[:ncol]
        datos.append([Paragraph(inline(c), s["celda"]) for c in f])

    t = Table(datos, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#33566f")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f6f8")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4ce")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def bloque_codigo(lineas, ancho_util):
    texto = "\n".join(lineas)
    mas_larga = max((len(l) for l in lineas), default=0)
    # Consolas: ancho de caracter ~0.55 em. Ajusta el cuerpo para que entre.
    cuerpo = 8.0
    if mas_larga > 0:
        cuerpo = min(8.0, (ancho_util - 10) / (mas_larga * 0.55))
        cuerpo = max(4.6, cuerpo)
    estilo = ParagraphStyle("code", fontName=MONO, fontSize=cuerpo,
                            leading=cuerpo * 1.22,
                            backColor=colors.HexColor("#f6f8fa"),
                            borderPadding=(5, 5, 5, 6),
                            textColor=colors.HexColor("#22303a"))
    return Preformatted(texto, estilo)


def convertir(ruta_md, ruta_pdf):
    with open(ruta_md, encoding="utf-8") as f:
        crudo = f.read()
    for viejo, nuevo in SUSTITUCIONES.items():
        crudo = crudo.replace(viejo, nuevo)
    lineas = crudo.split("\n")

    registrar_fuentes()
    s = estilos()

    doc = SimpleDocTemplate(
        ruta_pdf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=os.path.basename(ruta_md), author="TEL354 - Grupo 5",
    )
    ancho_util = doc.width

    # Separa texto de cuerpo y de codigo para verificar glifos por fuente.
    en_codigo, cuerpo_txt, codigo_txt = False, [], []
    for l in lineas:
        if l.strip().startswith("```"):
            en_codigo = not en_codigo
            continue
        (codigo_txt if en_codigo else cuerpo_txt).append(l)
    avisar_glifos_faltantes("\n".join(cuerpo_txt), "\n".join(codigo_txt))

    historia = []
    i, en_codigo, buffer_codigo = 0, False, []

    while i < len(lineas):
        linea = lineas[i]

        if linea.strip().startswith("```"):
            if en_codigo:
                historia.append(bloque_codigo(buffer_codigo, ancho_util))
                historia.append(Spacer(1, 7))
                buffer_codigo, en_codigo = [], False
            else:
                en_codigo = True
            i += 1
            continue

        if en_codigo:
            buffer_codigo.append(linea)
            i += 1
            continue

        if not linea.strip():
            i += 1
            continue

        # Tabla
        if linea.strip().startswith("|") and i + 1 < len(lineas) and es_separador(lineas[i + 1]):
            filas = [fila_tabla(linea)]
            i += 2
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                filas.append(fila_tabla(lineas[i]))
                i += 1
            historia.append(construir_tabla(filas, s, ancho_util))
            historia.append(Spacer(1, 9))
            continue

        # Cita (se agrupan lineas consecutivas)
        if linea.strip().startswith(">"):
            trozos = []
            while i < len(lineas) and lineas[i].strip().startswith(">"):
                trozos.append(lineas[i].strip().lstrip(">").strip())
                i += 1
            texto = " ".join(t for t in trozos if t)
            for parrafo in re.split(r"\s{0,}\|\|\s{0,}", texto):
                if parrafo.strip():
                    historia.append(Paragraph(inline(parrafo), s["quote"]))
                    historia.append(Spacer(1, 5))
            continue

        # Encabezados
        m = re.match(r"^(#{1,4})\s+(.*)$", linea)
        if m:
            nivel, texto = len(m.group(1)), m.group(2)
            clave = {1: "h1", 2: "h2", 3: "h3"}.get(nivel, "h3")
            historia.append(Paragraph(inline(texto), s[clave]))
            i += 1
            continue

        # Regla horizontal
        if re.match(r"^\s*([-*_])\1{2,}\s*$", linea):
            i += 1
            continue

        # Listas
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", linea)
        if m:
            historia.append(Paragraph(inline(m.group(2)), s["li"], bulletText="\u2022"))
            i += 1
            continue
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", linea)
        if m:
            historia.append(Paragraph(inline(m.group(3)), s["li"],
                                      bulletText=f"{m.group(2)}."))
            i += 1
            continue

        # Parrafo: acumula lineas hasta un corte
        trozos = []
        while i < len(lineas) and lineas[i].strip() and not re.match(
                r"^(#{1,4}\s|\s*[-*+]\s|\s*\d+\.\s|>|\||```)", lineas[i]):
            trozos.append(lineas[i].strip())
            i += 1
        if trozos:
            historia.append(Paragraph(inline(" ".join(trozos)), s["p"]))
        else:
            i += 1

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont(BODY, 7.5)
        canvas.setFillColor(colors.HexColor("#7a8792"))
        canvas.drawString(2 * cm, 1.1 * cm,
                          "TEL354 - Redes Definidas por Software - Grupo 5")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Pag. {documento.page}")
        canvas.restoreState()

    os.makedirs(os.path.dirname(os.path.abspath(ruta_pdf)), exist_ok=True)
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    print(f"Generado: {ruta_pdf}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: python scripts/md-a-pdf.py <entrada.md> <salida.pdf>")
    convertir(sys.argv[1], sys.argv[2])
