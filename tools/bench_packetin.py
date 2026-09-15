"""App de medicion del plano de control para la Fase 4 del reconocimiento VNRT.

Mide el techo de Packet-In/s del controlador y la latencia de instalacion de un
FLOW_MOD bajo carga, que es el dato del que depende el diseno de deteccion de R3.

No instala reglas de reenvio reales: la unica regla que instala es el table-miss
-> CONTROLLER (necesario en OF1.3 para que los table-miss generen Packet-In). La
latencia se mide con un FLOW_MOD "no-op" (matchea un puerto UDP que nunca se
envia, sin acciones = drop) seguido de un Barrier, de modo que no afecta el
trafico de prueba.

Controlador: os-ken (fork mantenido de Ryu). Los imports son os_ken.* porque Ryu
no instala en Python 3.12 (ver resultados-vnrt.md, Fase 4.0). La API es
equivalente a la de Ryu una a una.

Se lanza con el launcher propio tools/osken_run.py:
    python osken_run.py bench_packetin
"""

import os
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib import hub
from os_ken.ofproto import ofproto_v1_3


class PacketInBench(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    #: cada cuantos Packet-In se lanza una sonda de latencia FLOW_MOD+Barrier
    SAMPLE_EVERY = 200

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total = 0            # Packet-In acumulados
        self.window = 0           # Packet-In en el segundo en curso
        self.datapaths = {}
        self.pending = {}         # xid de Barrier -> t0 (monotonic)
        self.latencies = []       # RTT Packet-In->FLOW_MOD confirmado, en ms
        self._clk = os.sysconf("SC_CLK_TCK")
        self.monitor = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _features(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        psr = dp.ofproto_parser
        self.datapaths[dp.id] = dp
        # Unica regla instalada: table-miss -> CONTROLLER (truncado a 64 bytes
        # para minimizar la copia y estresar el plano de control, no el ancho de
        # banda del canal).
        match = psr.OFPMatch()
        actions = [psr.OFPActionOutput(ofp.OFPP_CONTROLLER, 64)]
        inst = [psr.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = psr.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst)
        dp.send_msg(mod)
        self.logger.info("switch conectado dpid=%016x, table-miss instalado", dp.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in(self, ev):
        self.total += 1
        self.window += 1
        if self.total % self.SAMPLE_EVERY == 0:
            self._probe_latency(ev.msg.datapath)

    def _probe_latency(self, dp):
        ofp = dp.ofproto
        psr = dp.ofproto_parser
        # FLOW_MOD no-op: matchea un puerto UDP que el generador nunca usa, con
        # hard_timeout corto. Sin instrucciones = drop. No toca el trafico real,
        # solo sirve para cronometrar el ciclo controlador->switch bajo carga.
        match = psr.OFPMatch(eth_type=0x0800, ip_proto=17, udp_dst=54321)
        mod = psr.OFPFlowMod(datapath=dp, priority=1, match=match,
                             instructions=[], hard_timeout=2, table_id=0)
        dp.send_msg(mod)
        barrier = psr.OFPBarrierRequest(dp)
        dp.set_xid(barrier)
        self.pending[barrier.xid] = time.monotonic()
        dp.send_msg(barrier)

    @set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
    def _barrier_reply(self, ev):
        t0 = self.pending.pop(ev.msg.xid, None)
        if t0 is not None:
            self.latencies.append((time.monotonic() - t0) * 1000.0)

    def _cpu_ticks(self):
        with open("/proc/self/stat") as f:
            parts = f.read().split()
        return int(parts[13]) + int(parts[14])  # utime + stime

    def _monitor(self):
        prev_ticks = self._cpu_ticks()
        prev_wall = time.monotonic()
        while True:
            hub.sleep(1)
            now = time.monotonic()
            ticks = self._cpu_ticks()
            dt = now - prev_wall
            cpu = 100.0 * (ticks - prev_ticks) / self._clk / dt if dt > 0 else 0.0
            prev_ticks, prev_wall = ticks, now
            if self.latencies:
                s = sorted(self.latencies)
                med = s[len(s) // 2]
                p95 = s[min(len(s) - 1, int(len(s) * 0.95))]
                lat = "med=%.2fms p95=%.2fms n=%d" % (med, p95, len(s))
            else:
                lat = "sin muestras"
            self.logger.info("PPS=%d total=%d cpu=%.1f%% lat[%s]",
                             self.window, self.total, cpu, lat)
            self.window = 0
