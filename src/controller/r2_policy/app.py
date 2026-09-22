"""App de os-ken para R2: restriccion de acceso a recursos privilegiados.

Implementa la tabla 3 del pipeline (docs/contratos/tablas-openflow.md):
lee el rol que R1 escribio en `metadata` y decide si el acceso a un
recurso critico procede o se descarta. El diseno completo esta en
docs/03-hld/r2-recursos-privilegiados.md; este archivo es su LLSD hecho
codigo.

El slice de recursos protegidos esta hardcodeado por ahora (ver
`SLICE_POR_DEFECTO` mas abajo) -- la Northbound API que lo cargaria en
produccion queda para un incremento posterior, igual que en R1.

Se lanza junto con R1 y el reenvio comun:

    python tools/osken_run.py \
        src.controller.r1_auth.app src.controller.r2_policy.app src.common.l2_forwarding
"""

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ethernet, icmp, ipv4, packet, tcp, udp
from os_ken.ofproto import ofproto_v1_3

from src.common import pipeline
from src.common.eventbus import bus
from src.controller.r2_policy.slice import (
    PRIO_DENIEGA_ATAQUE,
    PRIO_DENIEGA_HOST_TEMPORAL,
    Recurso,
    Slice,
)

IP_PROTO = {"icmp": 1, "tcp": 6, "udp": 17}

# Recursos protegidos de esta corrida: los mismos que el mapa real del VNRT
# (docs/diagramas/topologia-vnrt.md) marca como criticos en sw3.
SLICE_POR_DEFECTO = Slice("campus-recursos-privilegiados", [
    Recurso("servidor-notas", "10.0.0.3", "icmp", (),
            (pipeline.ROL_DOCENTE, pipeline.ROL_SUPERUSUARIO)),
    Recurso("repo-examenes", "10.0.0.4", "icmp", (),
            (pipeline.ROL_SUPERUSUARIO,)),
])


class PoliticaDeRecursosR2(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # noqa: RUF012 -- convencion de os-ken, no se muta

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slice = SLICE_POR_DEFECTO
        self.datapaths = {}
        bus.suscribir("ataque_detectado", self._al_recibir_ataque_detectado)

    # --- Ciclo de vida del switch -------------------------------------------

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _al_conectar(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self._instalar_slice(dp)
        self.logger.info("R2 activo en dpid=%016x, tabla %d (politica), slice=%s",
                          dp.id, pipeline.TABLA_POLITICA, self.slice.nombre)

    def _instalar_slice(self, dp):
        ofp, psr = dp.ofproto, dp.ofproto_parser

        # table-miss, red de seguridad: si por lo que sea nada mas coincide,
        # igual deja pasar (el defecto explicito de abajo es el que manda).
        self._instalar(dp, pipeline.PRIO_TABLE_MISS, psr.OFPMatch(),
                        [psr.OFPInstructionGotoTable(pipeline.TABLA_REENVIO)])

        for regla in self.slice.compilar():
            if regla.tipo == "defecto":
                self._instalar(dp, regla.prioridad, psr.OFPMatch(),
                                [psr.OFPInstructionGotoTable(pipeline.TABLA_REENVIO)])
                continue

            match_kwargs = {"eth_type": 0x0800, "ip_proto": IP_PROTO[regla.protocolo],
                             "ipv4_dst": regla.destino}
            if regla.puerto is not None:
                campo = "tcp_dst" if regla.protocolo == "tcp" else "udp_dst"
                match_kwargs[campo] = regla.puerto

            if regla.tipo == "permiso":
                metadata = pipeline.codificar_metadata(regla.rol, pipeline.ESTADO_AUTENTICADO)
                match = psr.OFPMatch(metadata=(metadata, pipeline.METADATA_MASCARA_ESCRITA_R1),
                                      **match_kwargs)
                inst = [psr.OFPInstructionGotoTable(pipeline.TABLA_REENVIO)]
            else:  # denegacion
                match = psr.OFPMatch(**match_kwargs)
                actions = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
                inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]

            self._instalar(dp, regla.prioridad, match, inst)

    @staticmethod
    def _instalar(dp, prioridad, match, inst, idle_timeout=0):
        psr = dp.ofproto_parser
        dp.send_msg(psr.OFPFlowMod(
            datapath=dp, table_id=pipeline.TABLA_POLITICA, priority=prioridad,
            match=match, instructions=inst, idle_timeout=idle_timeout))

    # --- Intento denegado: registrar y bloquear al host puntualmente -------

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        msg = ev.msg
        if msg.table_id != pipeline.TABLA_POLITICA:
            return  # no es una denegacion de la tabla de R2

        dp = msg.datapath
        in_port = msg.match["in_port"]
        metadata = msg.match.get("metadata", 0)
        rol, estado = pipeline.decodificar_metadata(metadata)

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if eth is None or ip_pkt is None:
            return

        proto, puerto = self._proto_y_puerto(pkt)
        recurso = self.slice.recurso_de(ip_pkt.dst, proto, puerto)
        nombre_recurso = recurso.nombre if recurso else "desconocido"

        self.logger.info(
            "acceso denegado: MAC=%s rol=%s estado=%s -> %s (%s) recurso=%s",
            eth.src, pipeline.NOMBRES_ROL.get(rol, rol), estado, ip_pkt.dst, proto, nombre_recurso)

        bus.publicar(
            "acceso_denegado",
            mac=eth.src, ip_origen=ip_pkt.src, ip_destino=ip_pkt.dst,
            recurso=nombre_recurso,
        )

        if recurso is not None:
            self._bloquear_host_temporalmente(dp, in_port, eth.src, ip_pkt.dst, proto, puerto)

    @staticmethod
    def _proto_y_puerto(pkt):
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        if tcp_pkt:
            return "tcp", tcp_pkt.dst_port
        if udp_pkt:
            return "udp", udp_pkt.dst_port
        if icmp_pkt:
            return "icmp", None
        return "ip-otro", None

    def _bloquear_host_temporalmente(self, dp, in_port, mac, destino, protocolo, puerto):
        """Regla de vida corta (10s) mas especifica que la denegacion
        generica del recurso: mientras dura, el switch descarta sin volver
        a molestar al controlador. HLD R2 S4, "Ciclo de vida de una
        denegacion". Al expirar, un atacante insistente genera un nuevo
        Packet-In -- esa senal es la que R3 usara como indicio temprano."""
        psr = dp.ofproto_parser
        match_kwargs = {"in_port": in_port, "eth_type": 0x0800, "eth_src": mac,
                         "ip_proto": IP_PROTO[protocolo], "ipv4_dst": destino}
        if puerto is not None:
            match_kwargs["tcp_dst" if protocolo == "tcp" else "udp_dst"] = puerto
        match = psr.OFPMatch(**match_kwargs)
        inst = [psr.OFPInstructionActions(dp.ofproto.OFPIT_APPLY_ACTIONS, [])]  # sin acciones = drop
        self._instalar(dp, PRIO_DENIEGA_HOST_TEMPORAL, match, inst, idle_timeout=10)

    # --- Propagacion de bloqueo ante un ataque confirmado -------------------

    def _al_recibir_ataque_detectado(self, mac=None, ip=None, **_resto):
        """R2 consume `ataque_detectado` (emitido por R3) y propaga el
        bloqueo del host a TODOS los switches conocidos, no solo al que
        vio el ataque -- HLD R2 S5: "acceso_denegado -> ataque_detectado:
        propaga el bloqueo al resto de switches"."""
        if not self.datapaths:
            self.logger.warning("ataque_detectado para MAC %s: sin switches conectados", mac)
            return
        for dp in self.datapaths.values():
            psr = dp.ofproto_parser
            match = psr.OFPMatch(eth_src=mac)
            inst = [psr.OFPInstructionActions(dp.ofproto.OFPIT_APPLY_ACTIONS, [])]
            self._instalar(dp, PRIO_DENIEGA_ATAQUE, match, inst)  # sin timeout: hasta accion manual
        self.logger.info("bloqueo propagado a %d switches: MAC=%s (motivo=ataque_detectado)",
                          len(self.datapaths), mac)
