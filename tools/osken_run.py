"""Launcher minimo para apps de os-ken.

El wheel de os-ken 4.2.2 en PyPI no incluye el modulo os_ken.cmd ni registra el
console-script osken-manager (ver resultados-vnrt.md, Fase 4.0). Su API interna
si esta completa, asi que este launcher reproduce lo que ryu-manager/osken-manager
hacen por dentro: cargar la app, crear contextos, instanciarla y levantar el
OpenFlowController.

Uso (desde el directorio que contiene el modulo de la app):
    python osken_run.py bench_packetin [opciones de os_ken.cfg ...]

Acepta mas de un modulo de app, para levantar varios en el mismo proceso
(por ejemplo R1 junto con el reenvio comun de la tabla 4):
    python osken_run.py src.controller.r1_auth.app src.common.l2_forwarding

Los argumentos se leen como modulos de app hasta el primero que empiece con
"-", que junto con todo lo que sigue se pasa como opcion de os_ken.cfg.

Por defecto el OpenFlowController escucha en 0.0.0.0:6653.
"""

import sys

from os_ken import cfg, log
from os_ken.base.app_manager import AppManager
from os_ken.controller.controller import OpenFlowController
from os_ken.lib import hub


def main():
    if len(sys.argv) < 2:
        sys.exit("uso: python osken_run.py <modulo_app> [<modulo_app> ...] [opciones os_ken.cfg]")
    app_modules = []
    resto = sys.argv[1:]
    while resto and not resto[0].startswith("-"):
        app_modules.append(resto.pop(0))
    if not app_modules:
        sys.exit("uso: python osken_run.py <modulo_app> [<modulo_app> ...] [opciones os_ken.cfg]")
    cfg.CONF(args=resto, project="os_ken")
    log.init_log()

    app_mgr = AppManager.get_instance()
    app_mgr.load_apps(app_modules)
    contexts = app_mgr.create_contexts()
    services = app_mgr.instantiate_apps(**contexts)

    ctlr = OpenFlowController()
    services.append(hub.spawn(ctlr))

    try:
        hub.joinall(services)
    except KeyboardInterrupt:
        pass
    finally:
        app_mgr.close()


if __name__ == "__main__":
    main()
