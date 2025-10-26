import os
import requests
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider

# -------------------- GitHub Provider --------------------
auth = GitHubProvider(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    base_url=os.getenv("ROOT_URL")
)

# -------------------- FastMCP Init --------------------
mcp = FastMCP(name="cml-mcp", auth=auth)

# -------------------- CML Init --------------------
CML_HOST = os.getenv("VIRL_HOST")
USERNAME = os.getenv("VIRL_USERNAME")
PASSWORD = os.getenv("VIRL_PASSWORD")
VERIFY_CERT = os.getenv("CML_VERIFY_CERT", "true").lower() == "true"

TOKEN = None

def get_token():
    global TOKEN
    if TOKEN:
        return TOKEN
    url = f"{CML_HOST}/api/v0/authenticate"
    resp = requests.post(url, json={"username": USERNAME, "password": PASSWORD}, verify=VERIFY_CERT)
    resp.raise_for_status()
    TOKEN = resp.json() if resp.headers.get("content-type","").startswith("application/json") else resp.text
    if isinstance(TOKEN, dict):
        TOKEN = TOKEN.get("token") or next(iter(TOKEN.values()))
    TOKEN = TOKEN.strip('"')
    return TOKEN

def cml_request(path, method="GET", data=None):
    global TOKEN
    url = f"{CML_HOST}/api/v0/{path}"
    headers = {"Authorization": f"Bearer {get_token()}"}

    resp = requests.request(method, url, headers=headers, json=data, verify=VERIFY_CERT)

    if resp.status_code == 401:
        # Token expired → clear cache and retry once
        TOKEN = None
        headers["Authorization"] = f"Bearer {get_token()}"
        resp = requests.request(method, url, headers=headers, json=data, verify=VERIFY_CERT)

    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return resp.text



# -------------------- LAB TOOLS --------------------
@mcp.tool()
def list_labs():
    """List all labs"""
    return cml_request("labs")

@mcp.tool()
def create_lab(title: str, description: str = ""):
    """Create a new lab"""
    payload = {"title": title, "description": description}
    return cml_request("labs", method="POST", data=payload)

@mcp.tool()
def start_lab(lab_id: str):
    """Start a lab"""
    return cml_request(f"labs/{lab_id}/start", method="PUT")

@mcp.tool()
def stop_lab(lab_id: str):
    """Stop a lab"""
    return cml_request(f"labs/{lab_id}/stop", method="PUT")

@mcp.tool()
def wipe_lab(lab_id: str):
    """Wipe a lab"""
    return cml_request(f"labs/{lab_id}/wipe", method="PUT")

@mcp.tool()
def delete_lab(lab_id: str):
    """Delete a lab"""
    return cml_request(f"labs/{lab_id}", method="DELETE")

# -------------------- NODE TOOLS --------------------
@mcp.tool()
def list_nodes(lab_id: str):
    """List nodes in a lab"""
    return cml_request(f"labs/{lab_id}/nodes")

@mcp.tool()
def create_node(lab_id: str, label: str, node_definition: str = "iosv", x: int = 100, y: int = 100):
    """Create a new node in a lab"""
    payload = {"label": label, "node_definition": node_definition, "x": x, "y": y}
    return cml_request(f"labs/{lab_id}/nodes", method="POST", data=payload)

@mcp.tool()
def start_node(lab_id: str, node_id: str):
    """Start a node"""
    return cml_request(f"labs/{lab_id}/nodes/{node_id}/state/start", method="PUT")

@mcp.tool()
def stop_node(lab_id: str, node_id: str):
    """Stop a node"""
    return cml_request(f"labs/{lab_id}/nodes/{node_id}/state/stop", method="PUT")

@mcp.tool()
def wipe_node(lab_id: str, node_id: str):
    """Wipe a node"""
    return cml_request(f"labs/{lab_id}/nodes/{node_id}/wipe_disks", method="PUT")

@mcp.tool()
def delete_node(lab_id: str, node_id: str):
    """Delete a node"""
    return cml_request(f"labs/{lab_id}/nodes/{node_id}", method="DELETE")

@mcp.tool()
def node_state(lab_id: str, node_id: str):
    """Get node state"""
    return cml_request(f"labs/{lab_id}/nodes/{node_id}")

@mcp.tool()
def node_console(lab_id: str, node_id: str, lines: int = 50):
    """Get recent console output from a node"""
    return cml_request(f"labs/{lab_id}/nodes/{node_id}/console_data?lines={lines}")

# -------------------- LINK TOOLS --------------------
@mcp.tool()
def list_links(lab_id: str):
    """List links in a lab"""
    return cml_request(f"labs/{lab_id}/links")

@mcp.tool()
def create_link(lab_id: str, n1: str, i1: str, n2: str, i2: str):
    """Create a link between two nodes/interfaces"""
    payload = {"n1": n1, "i1": i1, "n2": n2, "i2": i2}
    return cml_request(f"labs/{lab_id}/links", method="POST", data=payload)

@mcp.tool()
def delete_link(lab_id: str, link_id: str):
    """Delete a link"""
    return cml_request(f"labs/{lab_id}/links/{link_id}", method="DELETE")


# -------------------- RUN SERVER --------------------
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)



