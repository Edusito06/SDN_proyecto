"""Reenvio comun (tabla 4) y "de paso" temporal para las tablas sin modulo.

Dos responsabilidades, ambas de "comun" segun el contrato de tablas:

1. Tabla 4, reenvio L2 real: aprendizaje MAC -> puerto y flood mientras no se
   conoce el destino. Esto es definitivo, no un parche.
2. Tablas 0, 1 y 3, reglas "de paso" a prioridad de table-miss (0): mientras
   R3 (tablas 0-1) y R2 (tabla 3) no existan como modulos propios, un
   paquete tiene que poder atravesar igual todo el pipeline para llegar a la
   tabla 2 (R1) y a la 4. Esto SI es temporal: cuando R2 y R3 instalen su
   propio table-miss en su tabla, el de aqui queda redundante (no rompe
   nada, pero conviene retirarlo de este archivo en ese momento para no
   dejar reglas muertas).
"""

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ether_types, ethernet, packet
from os_ken.ofproto import ofproto_v1_3

from src.common import pipeline

TABLAS_DE_PASO = (
    (pipeline.TABLA_ANTISPOOF, pipeline.TABLA_MITIGACION),   # 0 -> 1, mientras R3 no exista
    (pipeline.TABLA_MITIGACION, pipeline.TABLA_IDENTIDAD),   # 1 -> 2, mientras R3 no exista
    (pipeline.TABLA_POLITICA, pipeline.TABLA_REENVIO),       # 3 -> 4, mientras R2 no exista
)


class ReenvioComun(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # noqa: RUF012 -- convencion de os-ken, no se muta

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}  # dpid -> {mac: puerto}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _al_conectar(self, ev):
        dp = ev.msg.datapath
        ofp, psr = dp.ofproto, dp.ofproto_parser

        for tabla_origen, tabla_siguiente in TABLAS_DE_PASO:
            match = psr.OFPMatch()
            inst = [psr.OFPInstructionGotoTable(tabla_siguiente)]
            dp.send_msg(psr.OFPFlowMod(
                datapath=dp, table_id=tabla_origen,
                priority=pipeline.PRIO_TABLE_MISS, match=match,
                instructions=inst))

        match = psr.OFPMatch()
        actions = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(psr.OFPFlowMod(
            datapath=dp, table_id=pipeline.TABLA_REENVIO,
            priority=pipeline.PRIO_TABLE_MISS, match=match, instructions=inst))

        self.logger.info(
            "switch conectado dpid=%016x: tablas de paso instaladas, tabla %d "
            "(reenvio) con table-miss activo", dp.id, pipeline.TABLA_REENVIO)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        if msg.table_id != pipeline.TABLA_REENVIO:
            return  # no es un miss de la tabla que este modulo atiende

        ofp, psr = dp.ofproto, dp.ofproto_parser
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port
        out_port = self.mac_to_port[dpid].get(eth.dst, ofp.OFPP_FLOOD)
        actions = [psr.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = psr.OFPMatch(in_port=in_port, eth_dst=eth.dst)
            inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            dp.send_msg(psr.OFPFlowMod(
                datapath=dp, table_id=pipeline.TABLA_REENVIO,
                priority=pipeline.PRIO_REENVIO_MIN, match=match,
                instructions=inst, idle_timeout=60))

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(psr.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data))
