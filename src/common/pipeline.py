"""Constantes del pipeline de tablas OpenFlow.

Fuente unica de verdad: `docs/contratos/tablas-openflow.md`. Ningun modulo
declara estos numeros por su cuenta -- todos importan de aqui, para que un
cambio futuro al contrato se haga en un solo lugar.
"""

# --- Tablas -----------------------------------------------------------------
TABLA_ANTISPOOF = 0     # R3
TABLA_MITIGACION = 1    # R3
TABLA_IDENTIDAD = 2     # R1
TABLA_POLITICA = 3      # R2
TABLA_REENVIO = 4       # comun

# --- Rangos de prioridad (excluyentes) --------------------------------------
PRIO_ADMIN_MIN, PRIO_ADMIN_MAX = 60000, 65535        # emergencias manuales
PRIO_R3_MIN, PRIO_R3_MAX = 50000, 59999
PRIO_R2_DENIEGA_MIN, PRIO_R2_DENIEGA_MAX = 40000, 49999
PRIO_R2_PERMITE_MIN, PRIO_R2_PERMITE_MAX = 30000, 39999
PRIO_R1_MIN, PRIO_R1_MAX = 20000, 29999
PRIO_REENVIO_MIN, PRIO_REENVIO_MAX = 10000, 19999    # comun
PRIO_DEFECTO_MIN, PRIO_DEFECTO_MAX = 1, 9999          # comun
PRIO_TABLE_MISS = 0                                   # comun

# --- Codificacion de metadata (R1 escribe, R2 lee, nadie mas modifica) ------
# Bits 0-3: rol. Bits 4-7: estado de sesion. Bits 8-63: reservado.
METADATA_MASCARA_ROL = 0x0F
METADATA_MASCARA_ESTADO = 0xF0
METADATA_MASCARA_ESCRITA_R1 = 0xFF  # rol + estado juntos

ROL_DESCONOCIDO = 0
ROL_ALUMNO = 1
ROL_DOCENTE = 2
ROL_ADMIN_RED = 3
ROL_SUPERUSUARIO = 4

ESTADO_SIN_AUTENTICAR = 0
ESTADO_AUTENTICADO = 1
ESTADO_REVOCADO = 2


def codificar_metadata(rol, estado):
    """(rol, estado) -> entero de metadata, tal como lo escribe R1."""
    return (rol & 0x0F) | ((estado & 0x0F) << 4)


def decodificar_metadata(metadata):
    """entero de metadata -> (rol, estado). Inverso de codificar_metadata."""
    return metadata & METADATA_MASCARA_ROL, (metadata & METADATA_MASCARA_ESTADO) >> 4
