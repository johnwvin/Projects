from virl2_client import ClientLibrary as Client
import time

client = Client(url="https://10.0.0.9", username="cisco", password="john1214")
lab_title = "mpls-lac-1"
labs = client.find_labs_by_title(lab_title)

if labs:
    lab = labs[0]
else:
    lab = client.create_lab(lab_title)

# Remove Any Nodes in Lab
for node in lab.nodes():
    try:
        lab.stop()
    except Exception:
        pass
    try:
        lab.wipe()
    except Exception:
        pass
    node.remove()


# Create Nodes
router_nodes = [
    "ce-router-1",
    "pe-router-1",
    "p-router-1",
    "p-router-2",
    "p-router-3",
    "pe-router-4",
    "ce-router-2"
]


for node in router_nodes:
    lab.create_node(label=node, node_definition="iosv")




# Start Nodes Carefully 
for node in lab.nodes():
    print(f"starting {node.label}...")
    node.start()
    time.sleep(120)