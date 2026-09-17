"""App de medicion para la Fase 5 del reconocimiento VNRT: banco de ataques.

Se conecta a los tres switches reales (sw1, sw2, sw3) y en todos hace lo
mismo: aprendizaje L2 minimo (MAC -> puerto, con flood mientras no se conoce
el destino) para que el trafico llegue de verdad extremo a extremo. Es
necesario porque tanto nmap como hping3 necesitan resolver ARP del objetivo
antes de poder mandar cualquier paquete IP, y el atacante (h4, en sw3) y el
objetivo (h1, en sw2) estan en switches distintos: sin reenvio real en los
tres switches, el ARP nunca cruza sw1 y ninguna herramienta llega a generar
trafico de ataque de verdad.

La topologia es un arbol sin ciclos (sw1 al centro, sw2 y sw3 como hojas), asi
que floodear lo desconocido no genera tormenta de broadcast ni hace falta
spanning tree.

Cada Packet-In se registra en un log JSONL (una linea = un evento) ANTES de
reenviarlo, con timestamp, switch, puerto de entrada, MACs, IPs, protocolo y
puertos L4. Ese log es la materia prima para tools/analizar_ataques.py, que
calcula, por escenario, cuantos eventos genero, cuantos destinos y puertos
distintos toco, y en cuanto tiempo -- los datos que piden los umbrales T,
N_dst, N_port, N_miss del HLD de R3.

Controlador: os-ken (ver resultados-vnrt.md, Fase 4.0, sobre por que no es
Ryu). Se lanza con tools/osken_run.py:
    python osken_run.py bench_ataques
"""

import json
import os
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.lib.packet import arp, ethernet, icmp, ipv4, packet, tcp, udp
from os_ken.lib.packet import ether_types
from os_ken.ofproto import ofproto_v1_3

LOG_PATH = os.path.expanduser("~/bench/ataques_log.jsonl")
FLUSH_CADA_S = 0.5


class BenchAtaques(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}   # dpid -> {mac: puerto}, aprendizaje L2 por switch
        self._buffer = []
        self._total = 0
        self._ventana = 0
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        self._fh = open(LOG_PATH, "a", buffering=1)
        self.logger.info("log de eventos en %s", LOG_PATH)
        hub.spawn(self._flusher)
        hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _features(self, ev):
        dp = ev.msg.datapath
        ofp, psr = dp.ofproto, dp.ofproto_parser
        match = psr.OFPMatch()
        actions = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, 128)]
        inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(psr.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst))
        self.logger.info("switch conectado dpid=%016x (aprendizaje L2)", dp.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        self._total += 1
        self._ventana += 1
        campos = self._extraer_campos(pkt)
        self._registrar(dp.id, in_port, eth, campos)
        self._reenviar(dp, in_port, eth, msg, campos)

    def _extraer_campos(self, pkt):
        """Un solo parseo, usado tanto para el log como para decidir el match
        de la regla que se instala (evita duplicar el analisis del paquete)."""
        campos = {}
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            campos.update(proto="arp", ip_src=arp_pkt.src_ip, ip_dst=arp_pkt.dst_ip,
                          arp_op=arp_pkt.opcode)
            return campos
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return campos
        campos.update(ip_src=ip_pkt.src, ip_dst=ip_pkt.dst, ip_proto=ip_pkt.proto)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        if tcp_pkt:
            campos.update(proto="tcp", sport=tcp_pkt.src_port, dport=tcp_pkt.dst_port,
                          flags=tcp_pkt.bits)
        elif udp_pkt:
            campos.update(proto="udp", sport=udp_pkt.src_port, dport=udp_pkt.dst_port)
        elif icmp_pkt:
            campos.update(proto="icmp", icmp_type=icmp_pkt.type)
        else:
            campos.update(proto="ip-otro")
        return campos

    def _registrar(self, dpid, in_port, eth, campos):
        rec = {
            "t": time.time(),
            "dpid": format(dpid, "016x"),
            "in_port": in_port,
            "eth_src": eth.src,
            "eth_dst": eth.dst,
            "eth_type": hex(eth.ethertype),
        }
        rec.update(campos)
        self._buffer.append(rec)

    def _reenviar(self, dp, in_port, eth, msg, campos):
        """Aprendizaje L2 solo para saber POR DONDE reenviar (puerto de
        salida). La regla que se instala para no volver a molestar al
        controlador matchea por quintupla (IP+puerto), no por par de MACs:
        si matcheara solo por MAC, el primer paquete de un escaneo de puertos
        instalaria una regla que dejaria invisibles los 999 restantes, que es
        exactamente el efecto que se detecto y corrigio en esta corrida."""
        ofp, psr = dp.ofproto, dp.ofproto_parser
        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        out_port = self.mac_to_port[dpid].get(eth.dst, ofp.OFPP_FLOOD)
        actions = [psr.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = self._match_por_flujo(psr, in_port, eth, campos)
            if match is not None:
                inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
                dp.send_msg(psr.OFPFlowMod(datapath=dp, priority=10, match=match,
                                           instructions=inst, idle_timeout=15))
            # si match es None (ARP u otro sin IP), no se instala regla:
            # siempre vuelve a pasar por el controlador, a proposito.

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(psr.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                     in_port=in_port, actions=actions, data=data))

    @staticmethod
    def _match_por_flujo(psr, in_port, eth, campos):
        proto = campos.get("proto")
        if proto == "tcp":
            return psr.OFPMatch(in_port=in_port, eth_type=0x0800, ip_proto=6,
                                ipv4_src=campos["ip_src"], ipv4_dst=campos["ip_dst"],
                                tcp_src=campos["sport"], tcp_dst=campos["dport"])
        if proto == "udp":
            return psr.OFPMatch(in_port=in_port, eth_type=0x0800, ip_proto=17,
                                ipv4_src=campos["ip_src"], ipv4_dst=campos["ip_dst"],
                                udp_src=campos["sport"], udp_dst=campos["dport"])
        if proto == "icmp":
            return psr.OFPMatch(in_port=in_port, eth_type=0x0800, ip_proto=1,
                                ipv4_src=campos["ip_src"], ipv4_dst=campos["ip_dst"])
        if proto == "ip-otro":
            return psr.OFPMatch(in_port=in_port, eth_type=0x0800,
                                ipv4_src=campos["ip_src"], ipv4_dst=campos["ip_dst"])
        return None  # arp u otro: nunca se cachea, siempre va al controlador

    def _flusher(self):
        while True:
            hub.sleep(FLUSH_CADA_S)
            if self._buffer:
                lote, self._buffer = self._buffer, []
                for rec in lote:
                    self._fh.write(json.dumps(rec) + "\n")

    def _monitor(self):
        while True:
            hub.sleep(1)
            self.logger.info("PPS=%d total=%d", self._ventana, self._total)
            self._ventana = 0
