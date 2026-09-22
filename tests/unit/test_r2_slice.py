"""Pruebas unitarias del modelo de slice de R2. Sin red, sin os_ken."""

import pytest

from src.common.pipeline import (
    PRIO_R2_DENIEGA_MIN,
    PRIO_R2_PERMITE_MAX,
    PRIO_R2_PERMITE_MIN,
    ROL_DOCENTE,
    ROL_SUPERUSUARIO,
)
from src.controller.r2_policy.slice import Recurso, Slice, compilar


def test_recurso_rechaza_protocolo_invalido():
    with pytest.raises(ValueError):
        Recurso("x", "10.0.0.3", "sctp", (443,), (ROL_DOCENTE,))


def test_recurso_tcp_udp_necesitan_puertos():
    with pytest.raises(ValueError):
        Recurso("x", "10.0.0.3", "tcp", (), (ROL_DOCENTE,))


def test_recurso_icmp_no_necesita_puertos():
    r = Recurso("ping-critico", "10.0.0.4", "icmp", (), (ROL_SUPERUSUARIO,))
    assert r.puertos == ()


def test_recurso_sin_roles_permitidos_es_invalido():
    with pytest.raises(ValueError):
        Recurso("x", "10.0.0.3", "tcp", (443,), ())


def test_compilar_genera_permiso_y_denegacion_por_cada_rol_y_puerto():
    recursos = [Recurso("notas", "10.0.0.3", "tcp", (443,), (ROL_DOCENTE, ROL_SUPERUSUARIO))]
    reglas = compilar(recursos)
    permisos = [r for r in reglas if r.tipo == "permiso"]
    denegaciones = [r for r in reglas if r.tipo == "denegacion"]
    defecto = [r for r in reglas if r.tipo == "defecto"]

    assert len(permisos) == 2  # un permiso por rol permitido
    assert {p.rol for p in permisos} == {ROL_DOCENTE, ROL_SUPERUSUARIO}
    assert len(denegaciones) == 1  # una denegacion generica para el recurso
    assert len(defecto) == 1  # siempre exactamente una regla de defecto


def test_ningun_recurso_queda_sin_su_denegacion_explicita():
    recursos = [
        Recurso("notas", "10.0.0.3", "icmp", (), (ROL_DOCENTE,)),
        Recurso("examenes", "10.0.0.4", "icmp", (), (ROL_SUPERUSUARIO,)),
    ]
    reglas = compilar(recursos)
    nombres_con_denegacion = {r.recurso for r in reglas if r.tipo == "denegacion"}
    assert nombres_con_denegacion == {"notas", "examenes"}


def test_prioridades_caen_en_el_rango_del_contrato():
    # El "defecto" tambien es politica de R2 (deja pasar lo que no es un
    # recurso controlado), asi que vive en el extremo bajo del rango de
    # permisos de R2 -- no en el rango comun -- igual que el ejemplo del
    # HLD R2 S4 (regla 7, prioridad 30000).
    #
    # La "denegacion" generica por recurso TAMBIEN cae en el rango de
    # permisos (mas abajo que el permiso mismo, mas arriba que el defecto):
    # en OpenFlow gana la prioridad mas alta sin importar la especificidad
    # del match, asi que si viviera en 40000-49999 le ganaria a cualquier
    # permiso valido -- bug real, encontrado probando contra el VNRT (ver
    # LLSD). El rango 40000-49999 queda para los bloqueos REACTIVOS
    # (host puntual, ataque confirmado), que si deben ganarle a un permiso.
    recursos = [Recurso("notas", "10.0.0.3", "tcp", (443,), (ROL_DOCENTE,))]
    for regla in compilar(recursos):
        assert PRIO_R2_PERMITE_MIN <= regla.prioridad <= PRIO_R2_PERMITE_MAX
        assert regla.prioridad < PRIO_R2_DENIEGA_MIN  # ninguna regla estatica invade el rango reactivo


def test_permiso_tiene_mayor_prioridad_que_la_denegacion_generica():
    # La prueba de regresion del bug real: en OpenFlow gana la prioridad
    # numerica mas alta sin importar la especificidad del match. Si la
    # denegacion generica de un recurso tuviera prioridad >= que su propio
    # permiso, un rol autorizado quedaria bloqueado igual.
    recursos = [Recurso("notas", "10.0.0.3", "tcp", (443,), (ROL_DOCENTE,))]
    reglas = compilar(recursos)
    permiso = next(r for r in reglas if r.tipo == "permiso")
    denegacion = next(r for r in reglas if r.tipo == "denegacion")
    assert permiso.prioridad > denegacion.prioridad


def test_slice_recurso_de_encuentra_coincidencia_exacta():
    s = Slice("prueba", [Recurso("notas", "10.0.0.3", "tcp", (443,), (ROL_DOCENTE,))])
    assert s.recurso_de("10.0.0.3", "tcp", 443).nombre == "notas"


def test_slice_recurso_de_devuelve_none_si_no_hay_match():
    s = Slice("prueba", [Recurso("notas", "10.0.0.3", "tcp", (443,), (ROL_DOCENTE,))])
    assert s.recurso_de("10.0.0.3", "tcp", 22) is None       # mismo host, otro puerto
    assert s.recurso_de("10.0.0.99", "tcp", 443) is None      # otro host


def test_slice_recurso_de_icmp_ignora_el_puerto():
    s = Slice("prueba", [Recurso("ping-critico", "10.0.0.4", "icmp", (), (ROL_SUPERUSUARIO,))])
    assert s.recurso_de("10.0.0.4", "icmp", None).nombre == "ping-critico"
