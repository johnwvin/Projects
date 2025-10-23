from virl2_client import ClientLibrary
from ipaddress import ip_interface
import os
import subprocess
import time
from netmiko import ConnectHandler

client = ClientLibrary(
    os.environ["VIRL_HOST"],
    os.environ["VIRL_USERNAME"],
    os.environ["VIRL_PASSWORD"],
    ssl_verify=False,
)

##########################################################################################################################

# Create Lab
LAB_TITLE = "multihome bgp LaC"
labs = client.find_labs_by_title(LAB_TITLE)
if labs:
    lab = labs[0]
else:
    lab = client.create_lab(LAB_TITLE)

##########################################################################################################################

# create nodes
for node in lab.nodes():
    try:
        node.stop()
    except Exception:
        pass
    try:
        node.wipe()
    except Exception:
        pass
    node.remove()

router_nodes = ["site-1-r1", "site-1-r2", "isp-1-r1", "isp-1-r2", "isp-1-r3", "isp-2-r1", "isp-2-r2", "isp-2-r3", "isp-3-r1", "isp-3-r2", "isp-3-r3", "site-2-r1", "site-2-r2"]

for name in router_nodes:
    lab.create_node(label=name, node_definition="iosv", x=100, y=100)
lab.create_node(label="mgmt-sw", node_definition="iosvl2", x=100, y=100, hide_links=True)
lab.create_node(label="mgmt", node_definition="external_connector", x=100, y=100, configuration="bridge0", hide_links=True)

##########################################################################################################################


# create interfaces
for n in lab.nodes():
    if n.label == "mgmt":
        continue
    for i in range(16):
        n.create_interface(i)

##########################################################################################################################


# define nodes

##site 1
site_1_r1 = lab.get_node_by_label("site-1-r1")
site_1_r2 = lab.get_node_by_label("site-1-r2")

##isp 1
isp_1_r1 = lab.get_node_by_label("isp-1-r1")
isp_1_r2 = lab.get_node_by_label("isp-1-r2")
isp_1_r3 = lab.get_node_by_label("isp-1-r3")

##isp 2
isp_2_r1 = lab.get_node_by_label("isp-2-r1")
isp_2_r2 = lab.get_node_by_label("isp-2-r2")
isp_2_r3 = lab.get_node_by_label("isp-2-r3")

##isp 3
isp_3_r1 = lab.get_node_by_label("isp-3-r1")
isp_3_r2 = lab.get_node_by_label("isp-3-r2")
isp_3_r3 = lab.get_node_by_label("isp-3-r3")

##site 2
site_2_r1 = lab.get_node_by_label("site-2-r1")
site_2_r2 = lab.get_node_by_label("site-2-r2")

## mgmt
mgmt_sw = lab.get_node_by_label("mgmt-sw")
mgmt = lab.get_node_by_label("mgmt")

##########################################################################################################################

# position nodes

## site 1
site_1_r1.x, site_1_r1.y = 100, 200
site_1_r2.x, site_1_r2.y = 100, 400

## isp 1
isp_1_r1.x, isp_1_r1.y = 300, 200
isp_1_r2.x, isp_1_r2.y = 300, 50
isp_1_r3.x, isp_1_r3.y = 500, 200

## isp 2
isp_2_r1.x, isp_2_r1.y = 300, 400
isp_2_r2.x, isp_2_r2.y = 300, 550
isp_2_r3.x, isp_2_r3.y = 500, 400

## isp 3
isp_3_r1.x, isp_3_r1.y = 700, 250
isp_3_r2.x, isp_3_r2.y = 900, 150
isp_3_r3.x, isp_3_r3.y = 900, 350

## site 2
site_2_r1.x, site_2_r1.y = 1100, 350
site_2_r2.x, site_2_r2.y = 1100, 550

## mgmt
mgmt_sw.x, mgmt_sw.y = 500, -200
mgmt.x, mgmt.y = 500, -300

##########################################################################################################################


# connect nodes
for link in lab.links():
    link.remove()

pairs_to_connect = [
    # Site 1
    ("site-1-r1", "site-1-r2"),
    ("site-1-r1", "isp-1-r1"),
    ("site-1-r2", "isp-2-r1"),
    ("site-1-r1", "mgmt-sw"),
    ("site-1-r2", "mgmt-sw"),
    ## isp 1
    ("isp-1-r1", "isp-1-r2"), 
    ("isp-1-r1", "isp-1-r3"), 
    ("isp-1-r2", "isp-1-r3"),
    ("isp-1-r1", "isp-2-r1"),
    ("isp-1-r3", "isp-3-r1"),
    ("isp-1-r1", "mgmt-sw"),
    ("isp-1-r2", "mgmt-sw"),
    ("isp-1-r3", "mgmt-sw"),
    ## isp 2
    ("isp-2-r1", "isp-2-r2"), 
    ("isp-2-r1", "isp-2-r3"),
    ("isp-2-r2", "isp-2-r3"),
    ("isp-2-r3", "isp-3-r1"),
    ("isp-2-r1", "mgmt-sw"),
    ("isp-2-r2", "mgmt-sw"),
    ("isp-2-r3", "mgmt-sw"),
    ## isp 3
    ("isp-3-r1", "isp-3-r2"),
    ("isp-3-r1", "isp-3-r3"),
    ("isp-3-r2", "isp-3-r3"),
    ("isp-3-r1", "mgmt-sw"),
    ("isp-3-r2", "mgmt-sw"),
    ("isp-3-r3", "mgmt-sw"),
    ## site 2
    ("site-2-r1", "isp-3-r3"),
    ("site-2-r2", "isp-3-r3"),
    ("site-2-r1", "site-2-r2"),
    ("site-2-r1", "mgmt-sw"),
    ("site-2-r2", "mgmt-sw"),
    ## mgmt
    ("mgmt-sw", "mgmt")
]

## map labels to node objects
node_map = {n.label: n for n in lab.nodes()}

for a, b in pairs_to_connect:
    n1 = node_map[a]
    n2 = node_map[b]

    ### check if already connected
    already_connected = any(
        set(link.nodes) == {n1, n2}
        for link in lab.links()
    )

    if not already_connected:
        lab.connect_two_nodes(n1, n2)

##########################################################################################################################


# Annotations
for ann in lab.annotations():
    ann.remove()

site_1_annotation = lab.create_annotation(
    x1=50, x2=150, y1=175, y2=275, color="#7EFF7F", annotation_type="rectangle"
)
isp_1_annotation = lab.create_annotation(
    x1=250, x2=300, y1=0, y2=250, color="#7EFFD7", annotation_type="rectangle"
)
isp_2_annotation = lab.create_annotation(
    x1=250, x2=300, y1=350, y2=250, color="#FF72C7", annotation_type="rectangle"
)
isp_3_annotation = lab.create_annotation(
    x1=650, x2=300, y1=125, y2=275, color="#BAB7FF", annotation_type="rectangle"
)
site_2_annotation = lab.create_annotation(
    x1=1000, x2=150, y1=325, y2=275, color="#7EFF7F", annotation_type="rectangle"
)

##########################################################################################################################

# Configure mgmt Interfaces
def mask(plen:int) -> str:
    return str(ip_interface(f"0.0.0.0/{plen}").netmask)

def ip_pool(network="192.168.100.0", start=1):
    base = ".".join(network.split(".")[:3])
    while True:
        yield f"{base}.{start}/24"
        start += 1

pool = ip_pool()
base = client._session.base_url
ext_link = mgmt_sw.get_link_to(mgmt)
ext_if = ext_link.interface_a if ext_link.interface_a.node == mgmt_sw else ext_link.interface_b
user_ssh_config = [
    "username john privilege 15 secret john1214\n"
    "line vty 0 4\n"
    " login local\n" 
    " transport input ssh\n"
    " transport output ssh\n"
    "ip domain-name johnwvin.com\n"
    "crypto key generate rsa modulus 2048\n"
    "ip ssh version 2\n"
]
l2_int_cfg = []
for ifc in mgmt_sw.physical_interfaces():
    if ifc.label == ext_if.label:
        continue
    l2_int_cfg.append(
        f"interface {ifc.label}\n"
        " switchport mode access\n"
        " switchport access vlan 100\n"
        " description MGMT\n"
        " no shutdown\n"
    )

# mgmt switch SVI
cfg_sw = (
    "vlan 100\n"
    " name MGMT\n"
    " exit\n"
    "interface Vlan100\n"
    " ip address 192.168.100.254 255.255.255.0\n"
    " no shutdown\n"
    " description MGMT\n"
    f"interface {ext_if.label}\n"
    " no switchport\n"
    " ip address 10.0.0.100 255.255.255.0\n"
    " no shutdown\n"
    " description MGMT\n"
    " exit\n"
    "spanning-tree vlan 100\n"
    + "".join(user_ssh_config)
    + "".join(l2_int_cfg)
)
client._session.patch(
    f"{base}/labs/{lab.id}/nodes/{mgmt_sw.id}",
    json={"configuration": cfg_sw},
).raise_for_status()
print("mgmt-sw configured")

# all routers: assign IP on interface that faces mgmt-sw
for node in lab.nodes():
    if node.node_definition == "external_connector" or node.label == "mgmt-sw":
        continue

    link = node.get_link_to(mgmt_sw)
    if not link:
        continue

    iface = link.interface_a if link.interface_a.node == node else link.interface_b

    cidr = next(pool)
    ip, plen = cidr.split("/")
    m = mask(int(plen))

    cfg = (
        f"hostname {node.label}\n"
        f"interface {iface.label}\n"
        f" ip address {ip} {m}\n"
        f" no shutdown\n"
        f" description MGMT\n"
        f"ip route 10.0.0.0 255.255.255.0 {iface.label} 192.168.100.254"
        +"".join(user_ssh_config)
    )

    client._session.patch(
        f"{base}/labs/{lab.id}/nodes/{node.id}",
        json={"configuration": cfg},
    ).raise_for_status()
    print(f"{node.label} configured {ip}/{plen} on {iface.label}")

##########################################################################################################################

def wait_for_reachability(ip, interval=180):
    print(f"Waiting for {ip} ...")
    while True:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(f"{ip} is reachable")
            return
        time.sleep(interval)

# 1. Start external connector
ext = lab.get_node_by_label("mgmt")
print("Starting external connector ...")
ext.start()

# 2. Start mgmt switch
print("Starting mgmt-sw ...")
mgmt_sw.start()
wait_for_reachability("192.168.100.254")

# 2a. Bounce Vlan Int
mgmt_sw_miko = {
    "device_type": "cisco_ios",
    "ip": "10.0.0.100",
    "username": "john",
    "password": "john1214"
}

config_commands = [
    "interface vlan 100",
    "shutdown",
    "no shutdown"
    ]

mgmt_sw_miko_connection = ConnectHandler(**mgmt_sw_miko)
mgmt_sw_miko_connection.send_config_set(config_commands)
mgmt_sw_miko_connection.save_config()
mgmt_sw_miko_connection.disconnect()

# 3. Start routers one at a time, wait for their mgmt IP
for node in lab.nodes():
    if node.node_definition == "external_connector" or node.label == "mgmt-sw":
        continue

    print(f"Starting {node.label} ...")
    node.start()

    # get the mgmt IP you assigned earlier by parsing its configuration
    ip = None
    for line in node.configuration.splitlines():
        if line.strip().startswith("ip address") and "192.168.100." in line:
            ip = line.split()[2]
            break
    if not ip:
        raise RuntimeError(f"No mgmt IP found in {node.label} configuration")

    wait_for_reachability(ip)

print("All nodes started and reachable.")

##########################################################################################################################