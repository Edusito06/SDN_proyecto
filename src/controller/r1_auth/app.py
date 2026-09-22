"""App de os-ken para R1: control de acceso a la red por rol.

Implementa la tabla 2 del pipeline (docs/contratos/tablas-openflow.md):
identifica al host por MAC + puerto de ingreso, le asigna un rol (tabla de
roles en memoria, `roles.py`) y escribe ese rol en `metadata` antes de
pasar el paquete a la tabla 3 (R2). El diseno completo esta en
docs/03-hld/r1-control-acceso.md; este archivo es su LLSD hecho codigo.

Se lanza junto con el reenvio comun (tabla 4) y las tablas de paso (0,1,3),
que hoy provee `src.common.l2_forwarding` mientras R2 y R3 no existan:

    python tools/osken_run.py src.controller.r1_auth.app src.common.l2_forwarding
"""

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ether_types, ethernet, packet
from os_ken.ofproto import ofproto_v1_3

from src.common import pipeline
from src.common.eventbus import bus
from src.controller.r1_auth.roles import TablaDeRoles


class ControlDeAccesoR1(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # noqa: RUF012 -- convencion de os-ken, no se muta

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.roles = TablaDeRoles()
        self.datapaths = {}   # dpid -> datapath, para poder revocar bajo demanda
        self.sesiones = {}    # mac -> {"dpid","in_port","rol","estado"}
        bus.suscribir("ataque_detectado", self._al_recibir_ataque_detectado)

    # --- Ciclo de vida del switch -------------------------------------------

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _al_conectar(self, ev):
        dp = ev.msg.datapath
        ofp, psr = dp.ofproto, dp.ofproto_parser
        self.datapaths[dp.id] = dp

        # table-miss de la tabla de identidad: cualquier host aun no
        # resuelto sube al controlador para que se le asigne rol.
        match = psr.OFPMatch()
        actions = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(psr.OFPFlowMod(
            datapath=dp, table_id=pipeline.TABLA_IDENTIDAD,
            priority=pipeline.PRIO_TABLE_MISS, match=match, instructions=inst))

        self.logger.info("R1 activo en dpid=%016x, tabla %d (identidad)",
                          dp.id, pipeline.TABLA_IDENTIDAD)

    # --- Identificacion de un host nuevo ------------------------------------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        msg = ev.msg
        if msg.table_id != pipeline.TABLA_IDENTIDAD:
            return  # no es un miss de la tabla de R1

        dp = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        mac = eth.src
        rol, es_desconocida = self.roles.resolver(mac)
        if es_desconocida:
            self.logger.info(
                "MAC no registrada %s en dpid=%016x puerto=%s: rol minimo "
                "(alumno) por defecto, evento de auditoria", mac, dp.id, in_port)

        self.sesiones[mac] = {
            "dpid": dp.id, "in_port": in_port,
            "rol": rol, "estado": pipeline.ESTADO_AUTENTICADO,
        }
        self._instalar_regla_identidad(dp, in_port, mac, rol, pipeline.ESTADO_AUTENTICADO)
        self._reenviar_paquete_original(dp, msg, in_port)

        bus.publicar(
            "host_autenticado",
            dpid=dp.id, in_port=in_port, mac=mac, rol=rol,
        )

    def _instalar_regla_identidad(self, dp, in_port, mac, rol, estado):
        psr = dp.ofproto_parser
        metadata = pipeline.codificar_metadata(rol, estado)
        match = psr.OFPMatch(in_port=in_port, eth_src=mac)
        inst = [
            psr.OFPInstructionWriteMetadata(metadata, pipeline.METADATA_MASCARA_ESCRITA_R1),
            psr.OFPInstructionGotoTable(pipeline.TABLA_POLITICA),
        ]
        # priority fija dentro del rango de R1: el match ya es tan
        # especifico (in_port + MAC exacta) que no hay solapamiento posible
        # entre reglas de este modulo.
        dp.send_msg(psr.OFPFlowMod(
            datapath=dp, table_id=pipeline.TABLA_IDENTIDAD,
            priority=pipeline.PRIO_R1_MIN, match=match, instructions=inst))

    def _reenviar_paquete_original(self, dp, msg, in_port):
        ofp, psr = dp.ofproto, dp.ofproto_parser
        # OFPP_TABLE reingresa el paquete por la tabla 0: con las reglas de
        # paso de src.common.l2_forwarding ya instaladas, vuelve a llegar
        # aqui pero esta vez coincide con la regla que se acaba de instalar.
        actions = [psr.OFPActionOutput(ofp.OFPP_TABLE)]
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(psr.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data))

    # --- Revocacion reactiva ante un ataque confirmado ----------------------

    def _al_recibir_ataque_detectado(self, mac=None, dpid=None, ip=None,
                                      tipo=None, confianza=None, **_resto):
        """R1 consume `ataque_detectado` (emitido por R3) y revoca la sesion
        del host, tal como describe el HLD R1 S6: "llega ataque_detectado ->
        R1 marca la sesion como revocada y emite sesion_revocada"."""
        sesion = self.sesiones.get(mac)
        if sesion is None:
            self.logger.warning(
                "ataque_detectado para MAC %s sin sesion activa en R1: nada que revocar", mac)
            return

        dp = self.datapaths.get(sesion["dpid"])
        if dp is None:
            self.logger.warning(
                "ataque_detectado para MAC %s: dpid=%016x sin datapath activo",
                mac, sesion["dpid"])
            return

        sesion["estado"] = pipeline.ESTADO_REVOCADO
        self._instalar_regla_identidad(dp, sesion["in_port"], mac, sesion["rol"],
                                        pipeline.ESTADO_REVOCADO)
        self.logger.info("sesion revocada: MAC=%s dpid=%016x (motivo=%s)", mac, dp.id, tipo)
        bus.publicar("sesion_revocada", mac=mac, ip=ip, motivo=tipo or "ataque_detectado")
