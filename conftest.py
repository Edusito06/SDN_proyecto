# Vacio a proposito: su unico trabajo es marcar la raiz del repo como rootdir
# de pytest, para que `from src...` funcione sin importar desde donde se
# invoque `pytest` (lo usa tests/unit, que no tiene __init__.py).
