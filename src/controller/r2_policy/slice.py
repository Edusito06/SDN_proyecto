"""Modelo declarativo del slice de R2 y su compilacion a reglas.

Traduce el `slice` de recursos privilegiados (HLD R2 S4) a una lista de
reglas abstractas -- sin ningun detalle de OpenFlow todavia, eso lo hace
`app.py`. Se puede probar con pytest normal, sin red ni os_ken.

Ejemplo minimo:

    recursos = [
        Recurso("servidor-notas", "10.0.0.3", "tcp", [443], [ROL_DOCENTE, ROL_SUPERUSUARIO]),
        Recurso("ping-critico", "10.0.0.4", "icmp", [], [ROL_SUPERUSUARIO]),
    ]
    reglas = compilar(recursos)
"""

from dataclasses import dataclass, field

from src.common.pipeline import (
    PRIO_DEFECTO_MIN,
    PRIO_R2_DENIEGA_MIN,
    PRIO_R2_PERMITE_MIN,
)

PROTOCOLOS_VALIDOS = {"tcp", "udp", "icmp"}

# En OpenFlow gana el numero de prioridad mas alto, sin importar que tan
# especifico sea el match de cada regla -- por eso el orden relativo entre
# estas tres constantes no es arbitrario, ver LLSD ("Bug encontrado en vivo").
#
# La denegacion GENERICA por recurso (cualquier rol que no tenga permiso)
# tiene que perder frente a un permiso valido, asi que va MAS ABAJO que
# PRIO_R2_PERMITE_MIN + 9000 (el permiso, en app.py) aunque conceptualmente
# sea una "denegacion". Los bloqueos REACTIVOS (host puntual, ataque
# confirmado) si tienen que ganarle a cualquier permiso -- esos si viven en
# el rango 40000-49999 que el contrato llama "denegaciones explicitas".
PRIO_DENIEGA_RECURSO = PRIO_R2_PERMITE_MIN + 5000         # 35000: entre defecto (30000) y permiso (39000)
PRIO_DENIEGA_HOST_TEMPORAL = PRIO_R2_DENIEGA_MIN + 5000   # 45000: bloqueo especifico de 10s, gana a cualquier permiso
PRIO_DENIEGA_ATAQUE = PRIO_R2_DENIEGA_MIN + 8000           # 48000: propagado por ataque_detectado, gana a cualquier permiso


@dataclass(frozen=True)
class Recurso:
    nombre: str
    destino: str          # IPv4, ej. "10.0.0.3"
    protocolo: str         # "tcp", "udp" o "icmp"
    puertos: tuple = ()    # vacio para icmp
    roles_permitidos: tuple = field(default_factory=tuple)

    def __post_init__(self):
        if self.protocolo not in PROTOCOLOS_VALIDOS:
            raise ValueError(f"protocolo invalido: {self.protocolo!r}")
        if self.protocolo != "icmp" and not self.puertos:
            raise ValueError(f"{self.nombre}: protocolo {self.protocolo} necesita al menos un puerto")
        if not self.roles_permitidos:
            raise ValueError(f"{self.nombre}: no tiene ningun rol permitido, no tiene sentido")


@dataclass(frozen=True)
class ReglaCompilada:
    tipo: str            # "permiso", "denegacion" o "defecto"
    prioridad: int
    recurso: str          # nombre del recurso, None para "defecto"
    destino: str = None
    protocolo: str = None
    puerto: int = None    # una regla por puerto individual
    rol: int = None       # solo en "permiso": el rol exacto que autoriza


def compilar(recursos):
    """Recursos -> lista de ReglaCompilada. Nunca deja un recurso sin su
    denegacion explicita (HLD R2 S4: "no hay solapes ni vacios")."""
    reglas = []
    for recurso in recursos:
        puertos = recurso.puertos or (None,)  # None = icmp, sin puerto
        for rol in recurso.roles_permitidos:
            for puerto in puertos:
                reglas.append(ReglaCompilada(
                    tipo="permiso", prioridad=PRIO_R2_PERMITE_MIN + 9000,
                    recurso=recurso.nombre, destino=recurso.destino,
                    protocolo=recurso.protocolo, puerto=puerto, rol=rol,
                ))
        for puerto in puertos:
            reglas.append(ReglaCompilada(
                tipo="denegacion", prioridad=PRIO_DENIEGA_RECURSO,
                recurso=recurso.nombre, destino=recurso.destino,
                protocolo=recurso.protocolo, puerto=puerto,
            ))

    reglas.append(ReglaCompilada(tipo="defecto", prioridad=PRIO_DEFECTO_MIN + 29999, recurso=None))
    return reglas


class Slice:
    def __init__(self, nombre, recursos):
        self.nombre = nombre
        self.recursos = list(recursos)

    def compilar(self):
        return compilar(self.recursos)

    def recurso_de(self, destino, protocolo, puerto):
        """Dado un destino/protocolo/puerto, el recurso que lo cubre (o
        None si no es un recurso controlado por este slice)."""
        for recurso in self.recursos:
            if recurso.destino != destino or recurso.protocolo != protocolo:
                continue
            if protocolo == "icmp" or puerto in recurso.puertos:
                return recurso
        return None
