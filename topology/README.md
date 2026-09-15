# Topología de laboratorio

El objetivo de esta carpeta es que la topología nunca más se arme a mano. Todo lo
que se hizo paso a paso en el Lab 1 (namespaces, pares veth, bridges OVS, subida
de interfaces) vive aquí como script, por tres razones: la demo del parcial tiene
que ser repetible, cualquier integrante puede levantar el entorno idéntico, y las
mediciones de KPI solo son comparables si parten del mismo estado.

## Acceso al entorno VNRT

Gateway de gestión `10.20.11.184`, con reenvío de puertos: Controller 5800,
SW1 5801, H1 5811. La red ploma no es enrutable desde fuera del entorno.

## Direccionamiento

| Red | Rango | Uso |
|---|---|---|
| Acceso (roja) | `192.168.0.0/24` | Hosts de usuario al switch OVS más cercano |
| SDN (ploma) | `10.0.0.0/24` | Switches entre sí y hacia el controlador |
| SDN (ploma) | `172.16.0.0/24` | Servidores y recursos privilegiados |

## Archivos previstos

| Archivo | Qué hace |
|---|---|
| `campus_topo.py` | Levanta la topología completa |
| `limpiar.sh` | Deja el entorno como estaba |
| `slices/laboratorio-redes.yaml` | Slice predefinido para la demo de R2 |

## Recordatorio de namespaces

Los comandos de OVS corren en el namespace por defecto, que es donde viven los
puertos internos del switch. Los comandos de los hosts virtuales necesitan
`ip netns exec <host> ...` por el aislamiento de namespaces.
