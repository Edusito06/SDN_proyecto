"""Resume un tramo del log de tools/bench_ataques.py como firma de un escenario.

Uso:
    python analizar_ataques.py ataques_log.jsonl <t_inicio> <t_fin> ["etiqueta"]

t_inicio y t_fin son epoch (segundos, con decimales), tomados del reloj del
nodo controller al lanzar y terminar cada comando de ataque -- para eso se
imprime `date +%s.%N` antes y despues de cada prueba en el runbook.

Imprime: total de eventos, IPs origen distintas, IPs destino distintas,
puertos destino distintos, tasa (eventos/s) y, si hay trafico TCP con flags,
un desglose de tipos.
"""

import json
import sys


def main():
    ruta = sys.argv[1]
    t0 = float(sys.argv[2])
    t1 = float(sys.argv[3])
    etiqueta = sys.argv[4] if len(sys.argv) > 4 else ruta

    eventos = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            rec = json.loads(linea)
            if t0 <= rec["t"] <= t1:
                eventos.append(rec)

    dur = max(t1 - t0, 1e-9)
    n = len(eventos)
    ip_src = {e.get("ip_src") for e in eventos if e.get("ip_src")}
    ip_dst = {e.get("ip_dst") for e in eventos if e.get("ip_dst")}
    dports = {e.get("dport") for e in eventos if e.get("dport") is not None}
    protos = {}
    for e in eventos:
        protos[e.get("proto", "?")] = protos.get(e.get("proto", "?"), 0) + 1

    print(f"=== {etiqueta} ===")
    print(f"ventana:            {dur:.2f} s  ({t0:.3f} -> {t1:.3f})")
    print(f"eventos (Packet-In): {n}")
    print(f"tasa:               {n / dur:.1f} eventos/s")
    print(f"IP origen distintas: {len(ip_src)}  {sorted(ip_src)}")
    print(f"IP destino distintas:{len(ip_dst)}  {sorted(ip_dst)[:20]}{' ...' if len(ip_dst) > 20 else ''}")
    print(f"puertos destino distintos: {len(dports)}")
    print(f"protocolos: {protos}")
    if eventos:
        print(f"primer evento: {eventos[0]}")
        print(f"ultimo evento: {eventos[-1]}")


if __name__ == "__main__":
    main()
