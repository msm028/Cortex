#!/usr/bin/env python3
"""Generate docs/inventory.md from machine-readable Governor sources."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_CATALOG = REPO_ROOT / "ops" / "inventory" / "host-catalog.json"
PORTS_REGISTRY = REPO_ROOT / "docs" / "runbooks" / "ports-registry.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "inventory.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.bin.project_manifest import discover_manifests, validate_manifest_payload  # noqa: E402


def now_local_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validated_manifests_for_root(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    manifests: list[dict[str, Any]] = []
    errors: list[str] = []
    base_dir = root / "projects"
    for path in discover_manifests(base_dir):
        try:
            payload = load_json(path)
        except Exception as exc:
            errors.append(f"{path}: failed to parse JSON ({exc})")
            continue
        manifest_errors = validate_manifest_payload(path, payload)
        if manifest_errors:
            errors.extend(manifest_errors)
            continue
        payload["_path"] = str(path.relative_to(root))
        manifests.append(payload)
    manifests.sort(key=lambda item: (item["project"]["key"], item["project"]["environment"]))
    return manifests, errors


def load_host_catalog(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError(f"{path}: expected version=1 host catalog object")
    hosts = payload.get("hosts")
    if not isinstance(hosts, list):
        raise ValueError(f"{path}: `hosts` must be a list")
    validated: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for raw in hosts:
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: each host entry must be an object")
        key = raw.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{path}: host `key` must be a non-empty string")
        key = key.strip()
        if key in seen_keys:
            raise ValueError(f"{path}: duplicate host key `{key}`")
        seen_keys.add(key)
        role = raw.get("role")
        management = raw.get("management")
        if not isinstance(role, str) or not role.strip():
            raise ValueError(f"{path}: host `{key}` missing non-empty `role`")
        if not isinstance(management, str) or not management.strip():
            raise ValueError(f"{path}: host `{key}` missing non-empty `management`")
        entry = {
            "key": key,
            "address": raw.get("address"),
            "role": role.strip(),
            "management": management.strip(),
            "iac_dir": raw.get("iac_dir"),
            "notes": str(raw.get("notes", "")).strip(),
        }
        validated.append(entry)
    return validated


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        value = value[1:-1]
    if value.isdigit():
        return int(value)
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def load_ports_registry(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("version:") or raw_line.strip() == "ports:":
            continue
        if raw_line.startswith("  - "):
            if current:
                entries.append(current)
            current = {}
            line = raw_line[4:]
        elif raw_line.startswith("    ") and current is not None:
            line = raw_line.strip()
        else:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = _parse_scalar(value)
    if current:
        entries.append(current)
    return entries


def _load_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = load_json(path)
    if not isinstance(payload, dict):
        return None
    return payload


def _extract_ip_from_state(payload: dict[str, Any]) -> str | None:
    outputs = payload.get("outputs")
    if isinstance(outputs, dict):
        ip_output = outputs.get("ip")
        if isinstance(ip_output, dict):
            value = ip_output.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    for resource in payload.get("resources", []):
        if not isinstance(resource, dict):
            continue
        for instance in resource.get("instances", []):
            if not isinstance(instance, dict):
                continue
            attrs = instance.get("attributes")
            if not isinstance(attrs, dict):
                continue
            for addresses in attrs.get("ipv4_addresses", []):
                if isinstance(addresses, list):
                    for address in addresses:
                        if isinstance(address, str) and address.strip():
                            return address.strip()
    return None


def _extract_tf_var_defaults(path: Path) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    if not path.is_file():
        return defaults
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r'variable\s+"([^"]+)"\s*{(.*?)}', text, re.S):
        name = match.group(1)
        body = match.group(2)
        value_match = re.search(r"default\s*=\s*(\"([^\"]*)\"|(\d+))", body)
        if value_match is None:
            continue
        if value_match.group(2) is not None:
            defaults[name] = value_match.group(2)
        elif value_match.group(3) is not None:
            defaults[name] = int(value_match.group(3))
    return defaults


def load_iac_facts(root: Path, host: dict[str, Any]) -> dict[str, Any]:
    iac_dir_raw = host.get("iac_dir")
    if not isinstance(iac_dir_raw, str) or not iac_dir_raw.strip():
        return {
            "status": "external",
            "source": "<none>",
            "vm_name": host["key"],
            "vm_id": None,
            "ip": None,
            "artifact": None,
        }

    iac_dir = root / iac_dir_raw
    state_path = iac_dir / "terraform.tfstate"
    state_payload = _load_json_if_present(state_path)
    if state_payload is not None:
        outputs = state_payload.get("outputs", {})
        vm_name = outputs.get("vm_name", {}).get("value") if isinstance(outputs, dict) else None
        vm_id = outputs.get("vm_id", {}).get("value") if isinstance(outputs, dict) else None
        return {
            "status": "applied",
            "source": "terraform.tfstate",
            "vm_name": vm_name or host["key"],
            "vm_id": vm_id,
            "ip": _extract_ip_from_state(state_payload),
            "artifact": str(state_path.relative_to(root)),
        }

    for plan_path in sorted(iac_dir.glob("*.plan.json")):
        plan_payload = _load_json_if_present(plan_path)
        if plan_payload is None:
            continue
        outputs = plan_payload.get("planned_values", {}).get("outputs", {})
        vm_name = outputs.get("vm_name", {}).get("value") if isinstance(outputs, dict) else None
        vm_id = outputs.get("vm_id", {}).get("value") if isinstance(outputs, dict) else None
        ip = outputs.get("ip", {}).get("value") if isinstance(outputs, dict) else None
        return {
            "status": "planned",
            "source": "plan.json",
            "vm_name": vm_name or host["key"],
            "vm_id": vm_id,
            "ip": ip if isinstance(ip, str) and ip.strip() else None,
            "artifact": str(plan_path.relative_to(root)),
        }

    defaults = _extract_tf_var_defaults(iac_dir / "variables.tf")
    return {
        "status": "declared",
        "source": "variables.tf",
        "vm_name": defaults.get("vm_name", host["key"]),
        "vm_id": defaults.get("vm_id"),
        "ip": None,
        "artifact": str((iac_dir / "variables.tf").relative_to(root)),
    }


def build_project_facts(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifests, errors = load_validated_manifests_for_root(root)
    if errors:
        raise ValueError("\n".join(errors))

    summaries: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        summary = {
            "key": project["key"],
            "name": project["name"],
            "environment": project["environment"],
            "runtime_host": targets["runtime_host"],
            "ingress_host": targets["ingress_host"],
            "data_host": targets["data_host"],
            "manifest_path": manifest["_path"],
        }
        summaries.append(summary)
        for route in manifest.get("routes", []):
            routes.append(
                {
                    "project_key": project["key"],
                    "environment": project["environment"],
                    "host": route["host"],
                    "service": route["service"],
                    "port": route["port"],
                    "runtime_host": targets["runtime_host"],
                    "ingress_host": targets["ingress_host"],
                    "manifest_path": manifest["_path"],
                }
            )
    return summaries, routes


def _project_assignments(host_key: str, summaries: list[dict[str, Any]]) -> int:
    total = 0
    for item in summaries:
        if host_key in (item["runtime_host"], item["ingress_host"], item["data_host"]):
            total += 1
    return total


def _build_operator_endpoints(ports: list[dict[str, Any]]) -> list[tuple[str, str]]:
    label_map = {
        "cortex-wiki": "hosted Governor wiki",
        "uptime-kuma": "Uptime Kuma dashboard",
        "docs-dev-server": "local docs development server",
        "ui-dev-server": "local UI development server",
    }
    endpoints: list[tuple[str, str]] = []
    for entry in sorted(ports, key=lambda item: (str(item.get("where", "")), int(item.get("port", 0)))):
        service = entry.get("service")
        where = entry.get("where")
        port = entry.get("port")
        if service not in label_map or not isinstance(where, str) or not isinstance(port, int):
            continue
        endpoints.append((f"http://{where}:{port}", label_map[service]))
    return endpoints


def _build_public_route_endpoints(routes: list[dict[str, Any]]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for route in sorted(routes, key=lambda item: (item["host"], item["project_key"], item["service"])):
        if route["host"] in seen:
            continue
        seen.add(route["host"])
        label = f"`{route['project_key']}` public route for `{route['service']}`"
        entries.append((f"https://{route['host']}", label))
    return entries


def render_inventory(root: Path, stamp: str | None = None) -> str:
    stamp = stamp or now_local_stamp()
    hosts = load_host_catalog(root / "ops" / "inventory" / "host-catalog.json")
    ports = load_ports_registry(root / "docs" / "runbooks" / "ports-registry.yaml")
    project_summaries, project_routes = build_project_facts(root)

    host_facts: dict[str, dict[str, Any]] = {}
    ports_by_host: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in ports:
        where = entry.get("where")
        if isinstance(where, str) and where.strip():
            ports_by_host[where.strip()].append(entry)

    for host in hosts:
        facts = load_iac_facts(root, host)
        address = facts.get("ip") or host.get("address")
        host_facts[host["key"]] = {
            **host,
            "address": address,
            "iac": facts,
            "ports": sorted(ports_by_host.get(host["key"], []), key=lambda item: int(item.get("port", 0))),
            "project_assignments": _project_assignments(host["key"], project_summaries),
        }

    lines = [
        "# Inventory",
        "",
        "Generated from machine-readable Governor sources.",
        "Edit the host catalog, IaC artifacts, ports registry, or project manifests and rerun `make inventory` instead of editing this page directly.",
        "",
        f"Generated: {stamp} (local)",
        "",
        "## Host Summary",
        "",
        "| Host | Role | Address | Management | IaC Status | Declared Ports | Project Assignments |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for host_key in sorted(host_facts):
        host = host_facts[host_key]
        lines.append(
            f"| `{host_key}` | "
            f"{host['role']} | "
            f"`{host['address'] or '<unknown>'}` | "
            f"`{host['management']}` | "
            f"`{host['iac']['status']}` | "
            f"{len(host['ports'])} | "
            f"{host['project_assignments']} |"
        )
    lines.append("")

    lines.extend(["## Host Details", ""])
    for host_key in sorted(host_facts):
        host = host_facts[host_key]
        iac = host["iac"]
        lines.extend(
            [
                f"### `{host_key}`",
                "",
                f"- Role: {host['role']}",
                f"- Address: `{host['address'] or '<unknown>'}`",
                f"- Management: `{host['management']}`",
                f"- IaC status: `{iac['status']}` via `{iac['source']}`",
                f"- IaC artifact: `{iac['artifact'] or '<none>'}`",
                f"- VM name: `{iac['vm_name'] or host_key}`",
                f"- VMID: `{iac['vm_id'] if iac['vm_id'] is not None else '<unknown>'}`",
            ]
        )
        if host.get("notes"):
            lines.append(f"- Notes: {host['notes']}")
        lines.append("")

    lines.extend(["## Declared Ports By Host", ""])
    for host_key in sorted(host_facts):
        lines.extend([f"### `{host_key}`", ""])
        host_ports = host_facts[host_key]["ports"]
        if not host_ports:
            lines.extend(["No declared ports.", ""])
            continue
        lines.extend(
            [
                "| Port | Proto | Service | Notes |",
                "| ---: | --- | --- | --- |",
            ]
        )
        for entry in host_ports:
            lines.append(
                f"| {entry.get('port', '<unknown>')} | "
                f"`{entry.get('proto', '<unknown>')}` | "
                f"`{entry.get('service', '<unknown>')}` | "
                f"{entry.get('notes', '')} |"
            )
        lines.append("")

    lines.extend(["## Project Targets", ""])
    if not project_summaries:
        lines.extend(["No project manifests found.", ""])
    else:
        lines.extend(
            [
                "| Project | Environment | Runtime Host | Ingress Host | Data Host | Manifest |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in project_summaries:
            lines.append(
                f"| `{item['key']}` | "
                f"`{item['environment']}` | "
                f"`{item['runtime_host']}` | "
                f"`{item['ingress_host']}` | "
                f"`{item['data_host']}` | "
                f"`{item['manifest_path']}` |"
            )
        lines.append("")

    lines.extend(["## Public Routes", ""])
    if not project_routes:
        lines.extend(["No public routes declared in project manifests.", ""])
    else:
        lines.extend(
            [
                "| Host | Project | Environment | Service | Port | Runtime Host | Ingress Host |",
                "| --- | --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for route in sorted(project_routes, key=lambda item: (item["host"], item["project_key"], item["service"])):
            lines.append(
                f"| `{route['host']}` | "
                f"`{route['project_key']}` | "
                f"`{route['environment']}` | "
                f"`{route['service']}` | "
                f"{route['port']} | "
                f"`{route['runtime_host']}` | "
                f"`{route['ingress_host']}` |"
            )
        lines.append("")

    lines.extend(["## Endpoints", ""])
    endpoint_entries = _build_operator_endpoints(ports) + _build_public_route_endpoints(project_routes)
    if not endpoint_entries:
        lines.extend(["No endpoints derived from current repo sources.", ""])
    else:
        for url, label in endpoint_entries:
            lines.append(f"- `{url}` - {label}")
        lines.append("")

    lines.extend(
        [
            "## Source Of Truth Links",
            "",
            "- Host catalog: `ops/inventory/host-catalog.json`",
            "- Ports registry: `docs/runbooks/ports-registry.yaml`",
            "- Project manifests: `projects/**/*.json`",
            "- IaC directories:",
            "  - `infra/proxmox/cortex-control/`",
            "  - `infra/proxmox/cortex-data/`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate docs/inventory.md from tracked Governor sources")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown output path")
    args = parser.parse_args()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    content = render_inventory(REPO_ROOT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
