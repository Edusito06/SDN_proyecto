"""Bus de eventos interno del controlador (modulo M06 del catalogo).

Implementa el patron message-queueing que usan R1, R2 y R3 para comunicarse
sin llamarse directamente entre si: cada uno publica eventos y se suscribe a
los que le interesan. Contrato completo en
`docs/contratos/tablas-openflow.md`.

Vive en memoria del proceso del controlador -- no es una cola externa. Eso
alcanza mientras el controlador sea una unica instancia (ver HLD, "Modelo de
control", que declara esto como decision de alcance para el Ex1); si el
proyecto evoluciona a un cluster, este modulo es el que habria que
reemplazar por una cola real (Redis, RabbitMQ) sin tocar los publishers ni
los subscribers.
"""

import logging
from collections import defaultdict

logger = logging.getLogger("eventbus")

EVENTOS_VALIDOS = {
    "host_autenticado",
    "sesion_revocada",
    "acceso_denegado",
    "ataque_detectado",
    "mitigacion_aplicada",
}


class EventBus:
    def __init__(self):
        self._suscriptores = defaultdict(list)

    def suscribir(self, evento, callback):
        if evento not in EVENTOS_VALIDOS:
            raise ValueError(
                f"'{evento}' no esta en el contrato de eventos "
                f"(docs/contratos/tablas-openflow.md): {sorted(EVENTOS_VALIDOS)}"
            )
        self._suscriptores[evento].append(callback)

    def publicar(self, evento, **carga_util):
        if evento not in EVENTOS_VALIDOS:
            raise ValueError(
                f"'{evento}' no esta en el contrato de eventos "
                f"(docs/contratos/tablas-openflow.md): {sorted(EVENTOS_VALIDOS)}"
            )
        logger.info("evento=%s %s", evento, carga_util)
        for callback in self._suscriptores[evento]:
            callback(**carga_util)


# Instancia compartida por todas las apps del mismo proceso de controlador.
# os-ken instancia cada AppManager una sola vez por proceso, asi que esto
# es seguro mientras R1/R2/R3 corran juntos en el mismo osken_run.py.
bus = EventBus()
