"""Pruebas unitarias de la codificacion de metadata del contrato de tablas
(docs/contratos/tablas-openflow.md: bits 0-3 rol, bits 4-7 estado de sesion)."""

import pytest

from src.common.pipeline import (
    ESTADO_AUTENTICADO,
    ESTADO_REVOCADO,
    ESTADO_SIN_AUTENTICAR,
    ROL_ADMIN_RED,
    ROL_ALUMNO,
    ROL_DESCONOCIDO,
    ROL_DOCENTE,
    ROL_SUPERUSUARIO,
    codificar_metadata,
    decodificar_metadata,
)

CASOS = [
    (ROL_DESCONOCIDO, ESTADO_SIN_AUTENTICAR),
    (ROL_ALUMNO, ESTADO_AUTENTICADO),
    (ROL_DOCENTE, ESTADO_AUTENTICADO),
    (ROL_ADMIN_RED, ESTADO_AUTENTICADO),
    (ROL_SUPERUSUARIO, ESTADO_REVOCADO),
]


@pytest.mark.parametrize("rol,estado", CASOS)
def test_codificar_decodificar_es_reversible(rol, estado):
    metadata = codificar_metadata(rol, estado)
    rol_leido, estado_leido = decodificar_metadata(metadata)
    assert (rol_leido, estado_leido) == (rol, estado)


def test_rol_y_estado_no_se_pisan_entre_si():
    # rol=alumno (1) + estado=revocado (2) no debe leerse como otro rol
    metadata = codificar_metadata(ROL_ALUMNO, ESTADO_REVOCADO)
    assert metadata == 0x21
    assert decodificar_metadata(metadata) == (ROL_ALUMNO, ESTADO_REVOCADO)


def test_bits_altos_reservados_no_se_tocan():
    # la mascara de escritura de R1 es 0xFF: no debe afectar bits 8+
    metadata = codificar_metadata(ROL_SUPERUSUARIO, ESTADO_AUTENTICADO)
    assert metadata <= 0xFF
