"""Tabla de roles de R1: identidad por MAC + puerto de ingreso.

Decision de alcance documentada en el HLD (docs/03-hld/r1-control-acceso.md,
S3 y AD-02 del documento de arquitectura del Lab 3): se elige MAC sobre
802.1X/RADIUS por velocidad de implementacion para el Ex1, y la debilidad de
que la MAC es falsificable la cubre R3 (tabla 0, terna IP+MAC+puerto).

Sin dependencias de os_ken ni de red: se prueba con pytest normal, sin
switch ni controlador reales (tests/unit/test_r1_roles.py).
"""

from src.common.pipeline import (
    ROL_ADMIN_RED,
    ROL_ALUMNO,
    ROL_DESCONOCIDO,
    ROL_DOCENTE,
    ROL_SUPERUSUARIO,
)

NOMBRES_ROL = {
    ROL_DESCONOCIDO: "desconocido",
    ROL_ALUMNO: "alumno",
    ROL_DOCENTE: "docente",
    ROL_ADMIN_RED: "administrador_red",
    ROL_SUPERUSUARIO: "superusuario",
}


class TablaDeRoles:
    """Rol por MAC. Se puebla via la Northbound API (aun no implementada) o,
    para pruebas, pasando `roles_iniciales` directamente."""

    def __init__(self, roles_iniciales=None):
        self._roles = dict(roles_iniciales or {})

    def registrar(self, mac, rol):
        if rol not in NOMBRES_ROL:
            raise ValueError(f"rol invalido: {rol}. Validos: {sorted(NOMBRES_ROL)}")
        self._roles[mac] = rol

    def resolver(self, mac):
        """MAC conocida -> su rol, `es_desconocida=False`.
        MAC no registrada -> rol minimo (alumno) y `es_desconocida=True`,
        para que quien llama pueda registrar el evento de auditoria (HLD R1
        S3: "Si no esta registrada, aplica rol minimo por defecto... y
        registra el evento para auditoria")."""
        if mac in self._roles:
            return self._roles[mac], False
        return ROL_ALUMNO, True

    def __len__(self):
        return len(self._roles)
