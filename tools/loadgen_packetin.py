"""Generador de carga para la Fase 4 (medicion del plano de control del VNRT).

Envia tramas UDP a la direccion de broadcast del segmento de datos. Cada trama
es un unknown/broadcast que hace table-miss en el switch (que solo tiene la regla
table-miss -> CONTROLLER del bench), asi que genera un Packet-In por trama. No
necesita root ni scapy: usa solo la biblioteca estandar y SO_BROADCAST.

Uso, directo en la shell del host (sin ip netns; los hosts del VNRT son VMs):
    python3 loadgen_packetin.py <rate_pps> <duracion_s> [broadcast] [src_ip]
    rate_pps = 0  -> tan rapido como pueda (para buscar saturacion)
"""

import socket
import sys
import time


def main():
    rate = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    bcast = sys.argv[3] if len(sys.argv) > 3 else "10.0.0.255"
    src = sys.argv[4] if len(sys.argv) > 4 else "10.0.0.1"

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((src, 0))
    payload = b"x" * 32
    dst = (bcast, 9999)

    sent = 0
    start = time.time()
    end = start + dur
    if rate <= 0:
        while time.time() < end:
            s.sendto(payload, dst)
            sent += 1
    else:
        interval = 1.0 / rate
        nxt = time.time()
        while time.time() < end:
            s.sendto(payload, dst)
            sent += 1
            nxt += interval
            delay = nxt - time.time()
            if delay > 0:
                time.sleep(delay)
    elapsed = time.time() - start
    print("enviados=%d en %.2fs = %.0f pps efectivos" % (sent, elapsed, sent / elapsed))


if __name__ == "__main__":
    main()
