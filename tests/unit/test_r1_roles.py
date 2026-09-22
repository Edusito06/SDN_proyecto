"""Pruebas unitarias de la tabla de roles de R1. Sin red, sin os_ken."""

import pytest

from src.common.pipeline import ROL_ALUMNO, ROL_DOCENTE, ROL_SUPERUSUARIO
from src.controller.r1_auth.roles import TablaDeRoles


def test_mac_registrada_devuelve_su_rol():
    tabla = TablaDeRoles({"aa:bb:cc:dd:ee:01": ROL_DOCENTE})
    rol, es_desconocida = tabla.resolver("aa:bb:cc:dd:ee:01")
    assert rol == ROL_DOCENTE
    assert es_desconocida is False


def test_mac_no_registrada_degrada_a_alumno_y_marca_auditoria():
    tabla = TablaDeRoles()
    rol, es_desconocida = tabla.resolver("aa:bb:cc:dd:ee:99")
    assert rol == ROL_ALUMNO
    assert es_desconocida is True


def test_registrar_sobrescribe_el_rol_anterior():
    tabla = TablaDeRoles({"aa:bb:cc:dd:ee:01": ROL_ALUMNO})
    tabla.registrar("aa:bb:cc:dd:ee:01", ROL_SUPERUSUARIO)
    rol, es_desconocida = tabla.resolver("aa:bb:cc:dd:ee:01")
    assert rol == ROL_SUPERUSUARIO
    assert es_desconocida is False


def test_registrar_rechaza_rol_invalido():
    tabla = TablaDeRoles()
    with pytest.raises(ValueError):
        tabla.registrar("aa:bb:cc:dd:ee:01", rol=99)


def test_len_cuenta_solo_macs_registradas():
    tabla = TablaDeRoles({"aa:bb:cc:dd:ee:01": ROL_ALUMNO})
    tabla.resolver("aa:bb:cc:dd:ee:99")  # consultar una desconocida no la registra
    assert len(tabla) == 1
