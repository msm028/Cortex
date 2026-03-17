#!/usr/bin/env python3
"""Validate project manifests and render generated documentation artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT / "projects"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "projects.md"
DEFAULT_ROUTE_PREVIEW_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-route-preview.md"
DEFAULT_DEPLOY_PLAN_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-deploy-plan.md"
DEFAULT_BOOTSTRAP_CHECKLIST_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-bootstrap-checklist.md"
DEFAULT_RUNTIME_SKELETON_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-runtime-skeleton.md"
DEFAULT_ENV_CONTRACT_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-env-contract.md"
DEFAULT_SMOKE_CHECK_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-smoke-check.md"
DEFAULT_HANDOFF_PACKET_OUTPUT = REPO_ROOT / "docs" / "runbooks" / "generated" / "project-handoff-packet.md"
ALLOWED_ENVIRONMENTS = {"dev", "staging", "prod"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_manifests(base_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in base_dir.rglob("*.json")
        if path.is_file()
    )


def _require_dict(payload: Any, path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        errors.append(f"{path}: `{label}` must be an object")
        return {}
    return payload


def _require_string(parent: dict[str, Any], key: str, path: Path, errors: list[str]) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: `{key}` must be a non-empty string")
        return ""
    return value.strip()


def _require_bool(parent: dict[str, Any], key: str, path: Path, errors: list[str], default: bool | None = None) -> bool:
    if key not in parent:
        if default is not None:
            return default
        errors.append(f"{path}: `{key}` must be a boolean")
        return False
    value = parent.get(key)
    if not isinstance(value, bool):
        errors.append(f"{path}: `{key}` must be a boolean")
        return False
    return value


def validate_manifest_payload(path: Path, payload: Any) -> list[str]:
    errors: list[str] = []
    root = _require_dict(payload, path, "root", errors)
    if not root:
        return errors

    schema_version = root.get("schema_version")
    if schema_version != 1:
        errors.append(f"{path}: `schema_version` must equal 1")

    project = _require_dict(root.get("project"), path, "project", errors)
    project_key = _require_string(project, "key", path, errors)
    _require_string(project, "name", path, errors)
    environment = _require_string(project, "environment", path, errors)
    if environment and environment not in ALLOWED_ENVIRONMENTS:
        errors.append(f"{path}: `project.environment` must be one of {sorted(ALLOWED_ENVIRONMENTS)}")

    targets = _require_dict(root.get("targets"), path, "targets", errors)
    for key in ("runtime_host", "ingress_host", "data_host"):
        _require_string(targets, key, path, errors)

    domains = _require_dict(root.get("domains", {}), path, "domains", errors)
    public_domains = domains.get("public", [])
    if public_domains and (
        not isinstance(public_domains, list)
        or not all(isinstance(item, str) and item.strip() for item in public_domains)
    ):
        errors.append(f"{path}: `domains.public` must be a list of non-empty strings")
        public_domains = []

    services = _require_dict(root.get("services"), path, "services", errors)
    if not services:
        errors.append(f"{path}: `services` must define at least one service")
    enabled_services: set[str] = set()
    for service_name, raw in sorted(services.items()):
        if not isinstance(service_name, str) or not service_name.strip():
            errors.append(f"{path}: service keys must be non-empty strings")
            continue
        service = _require_dict(raw, path, f"services.{service_name}", errors)
        enabled = _require_bool(service, "enabled", path, errors, default=False)
        service_type = service.get("type")
        if service_type is not None and not isinstance(service_type, str):
            errors.append(f"{path}: `services.{service_name}.type` must be a string when provided")
        shared = service.get("shared")
        if shared is not None and not isinstance(shared, bool):
            errors.append(f"{path}: `services.{service_name}.shared` must be a boolean when provided")
        extensions = service.get("extensions", [])
        if extensions and (
            not isinstance(extensions, list)
            or not all(isinstance(item, str) and item.strip() for item in extensions)
        ):
            errors.append(f"{path}: `services.{service_name}.extensions` must be a list of strings")
        if enabled:
            enabled_services.add(service_name)

    routes = root.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append(f"{path}: `routes` must be a non-empty list")
        routes = []
    seen_hosts: set[str] = set()
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"{path}: `routes[{index}]` must be an object")
            continue
        host = route.get("host")
        if not isinstance(host, str) or not host.strip():
            errors.append(f"{path}: `routes[{index}].host` must be a non-empty string")
        elif host in seen_hosts:
            errors.append(f"{path}: duplicate route host `{host}`")
        else:
            seen_hosts.add(host)
            if public_domains and host not in public_domains:
                errors.append(f"{path}: route host `{host}` is not declared in `domains.public`")
        service_name = route.get("service")
        if not isinstance(service_name, str) or not service_name.strip():
            errors.append(f"{path}: `routes[{index}].service` must be a non-empty string")
        elif service_name not in services:
            errors.append(f"{path}: route service `{service_name}` is not defined")
        elif service_name not in enabled_services:
            errors.append(f"{path}: route service `{service_name}` is not enabled")
        port = route.get("port")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            errors.append(f"{path}: `routes[{index}].port` must be an integer between 1 and 65535")

    secrets = _require_dict(root.get("secrets"), path, "secrets", errors)
    vaultwarden_items = secrets.get("vaultwarden_items")
    if not isinstance(vaultwarden_items, list) or not all(
        isinstance(item, str) and item.strip() for item in vaultwarden_items
    ):
        errors.append(f"{path}: `secrets.vaultwarden_items` must be a list of non-empty strings")

    if project_key and "/" in project_key:
        errors.append(f"{path}: `project.key` must not contain `/`")

    return errors


def load_validated_manifests(base_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    manifests: list[dict[str, Any]] = []
    errors: list[str] = []
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
        payload["_path"] = str(path.relative_to(REPO_ROOT))
        manifests.append(payload)
    manifests.sort(key=lambda item: (item["project"]["key"], item["project"]["environment"]))
    return manifests, errors


def render_catalog(manifests: list[dict[str, Any]]) -> str:
    lines = [
        "# Project Catalog",
        "",
        "Generated from machine-readable project manifests under `projects/`.",
        "Edit manifests in `projects/` and rerun `make project-catalog` instead of editing this page directly.",
        "",
    ]
    if not manifests:
        lines.extend(
            [
                "No project manifests found.",
                "",
                "Create project manifests in `projects/` and rerun `make project-catalog`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Runtime Host | Ingress Host | Data Host | Routes | Path |",
            "| --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        route_count = len(manifest.get("routes", []))
        lines.append(
            f"| `{project['key']}` | "
            f"`{project['environment']}` | "
            f"`{targets['runtime_host']}` | "
            f"`{targets['ingress_host']}` | "
            f"`{targets['data_host']}` | "
            f"{route_count} | "
            f"`{manifest['_path']}` |"
        )
    lines.append("")

    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        domains = manifest.get("domains", {}).get("public", [])
        services = manifest.get("services", {})
        enabled = [
            f"{name} ({service.get('type', 'generic')})"
            for name, service in sorted(services.items())
            if isinstance(service, dict) and service.get("enabled")
        ]
        lines.extend(
            [
                f"## {project['name']}",
                "",
                f"- Key: `{project['key']}`",
                f"- Environment: `{project['environment']}`",
                f"- Runtime host: `{targets['runtime_host']}`",
                f"- Ingress host: `{targets['ingress_host']}`",
                f"- Data host: `{targets['data_host']}`",
                f"- Manifest: `{manifest['_path']}`",
                f"- Public domains: {', '.join(f'`{item}`' for item in domains) if domains else '`<none>`'}",
                f"- Enabled services: {', '.join(f'`{item}`' for item in enabled) if enabled else '`<none>`'}",
                "",
                "| Route Host | Service | Port |",
                "| --- | --- | ---: |",
            ]
        )
        for route in manifest.get("routes", []):
            lines.append(
                f"| `{route['host']}` | `{route['service']}` | {route['port']} |"
            )
        lines.append("")
    return "\n".join(lines)


def _build_route_preview_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_hosts: dict[str, str] = {}
    for manifest in manifests:
        project = manifest["project"]
        services = manifest.get("services", {})
        runtime_host = manifest["targets"]["runtime_host"]
        manifest_path = manifest["_path"]
        routes = sorted(
            manifest.get("routes", []),
            key=lambda route: (route["host"], route["service"], route["port"]),
        )
        for route in routes:
            host = route["host"]
            if host in seen_hosts:
                errors.append(
                    f"duplicate route host `{host}` across manifests "
                    f"(`{seen_hosts[host]}` and `{manifest_path}`)"
                )
                continue
            seen_hosts[host] = manifest_path
            service = services.get(route["service"], {})
            entries.append(
                {
                    "project_key": project["key"],
                    "project_name": project["name"],
                    "environment": project["environment"],
                    "manifest_path": manifest_path,
                    "host": host,
                    "service": route["service"],
                    "service_type": service.get("type", "generic"),
                    "upstream": f"{runtime_host}:{route['port']}",
                }
            )
    return entries, errors


def render_caddy_route_preview(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_route_preview_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project manifest Caddy route preview",
        "# Generated from validated manifests under `projects/`.",
        "# Preview only. This file does not change live routing.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "# No routes were found in validated manifests.",
                "",
            ]
        )
        return "\n".join(lines)

    current_group: tuple[str, str, str] | None = None
    for entry in entries:
        group = (entry["project_key"], entry["environment"], entry["manifest_path"])
        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.extend(
                [
                    f"# {entry['project_name']} ({entry['environment']})",
                    f"# Manifest: {entry['manifest_path']}",
                ]
            )
            current_group = group
        lines.extend(
            [
                f"{entry['host']} {{",
                f"\t# service: {entry['service']} ({entry['service_type']})",
                f"\treverse_proxy {entry['upstream']}",
                "}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def render_route_preview_doc(manifests: list[dict[str, Any]]) -> str:
    caddy_preview = render_caddy_route_preview(manifests).rstrip()
    lines = [
        "# Project Route Preview",
        "",
        "Generated from validated project manifests under `projects/`.",
        "This artifact is preview-only and does not update live routing.",
        "Edit manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py route-preview`.",
        "",
        "```caddyfile",
        caddy_preview,
        "```",
        "",
    ]
    return "\n".join(lines)


def _build_enabled_services(services: dict[str, Any]) -> list[dict[str, Any]]:
    enabled_services = []
    for service_name, raw in sorted(services.items()):
        if not isinstance(raw, dict) or not raw.get("enabled"):
            continue
        extensions = raw.get("extensions", [])
        if not isinstance(extensions, list):
            extensions = []
        enabled_services.append(
            {
                "name": service_name,
                "type": raw.get("type", "generic"),
                "shared": bool(raw.get("shared", False)),
                "extensions": sorted(
                    item for item in extensions if isinstance(item, str) and item.strip()
                ),
            }
        )
    return enabled_services


def _build_deploy_plan_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    _, route_errors = _build_route_preview_entries(manifests)
    if route_errors:
        return entries, route_errors

    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        services = manifest.get("services", {})
        enabled_services = _build_enabled_services(services)

        routes = sorted(
            manifest.get("routes", []),
            key=lambda route: (route["host"], route["service"], route["port"]),
        )
        secrets = sorted(
            item
            for item in manifest.get("secrets", {}).get("vaultwarden_items", [])
            if isinstance(item, str) and item.strip()
        )
        entries.append(
            {
                "project_key": project["key"],
                "project_name": project["name"],
                "environment": project["environment"],
                "manifest_path": manifest["_path"],
                "targets": {
                    "runtime": targets["runtime_host"],
                    "ingress": targets["ingress_host"],
                    "data": targets["data_host"],
                },
                "enabled_services": enabled_services,
                "routes": routes,
                "secrets": secrets,
            }
        )

    return entries, []


def _build_bootstrap_checklist_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    _, route_errors = _build_route_preview_entries(manifests)
    if route_errors:
        return entries, route_errors

    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        enabled_services = _build_enabled_services(manifest.get("services", {}))
        routes = sorted(
            manifest.get("routes", []),
            key=lambda route: (route["host"], route["service"], route["port"]),
        )
        secrets = sorted(
            item
            for item in manifest.get("secrets", {}).get("vaultwarden_items", [])
            if isinstance(item, str) and item.strip()
        )
        runtime_services = [service for service in enabled_services if not service["shared"]]
        shared_dependencies = [service for service in enabled_services if service["shared"]]
        routed_ports = sorted({route["port"] for route in routes})
        route_dependencies = [
            {
                "host": route["host"],
                "service": route["service"],
                "port": route["port"],
                "dependency": f"{targets['ingress_host']} -> {targets['runtime_host']}:{route['port']}",
            }
            for route in routes
        ]
        prerequisite_checks = [
            f"Confirm runtime host `{targets['runtime_host']}` exists and operator SSH/sudo access is ready.",
            f"Confirm Docker Engine and the Docker Compose plugin are installed on `{targets['runtime_host']}`.",
            f"Confirm `{targets['runtime_host']}` has outbound access for image pulls, package retrieval, and operator SSH management.",
        ]
        if routed_ports:
            port_list = ", ".join(f"`{port}`" for port in routed_ports)
            prerequisite_checks.append(
                f"Confirm ingress host `{targets['ingress_host']}` can reach `{targets['runtime_host']}` on routed ports {port_list}."
            )
        prerequisite_checks.append(
            f"Confirm dependency hosts remain available for this plan: ingress `{targets['ingress_host']}`, data `{targets['data_host']}`."
        )
        if secrets:
            prerequisite_checks.append(
                f"Confirm operators can resolve Vaultwarden references before any manual bootstrap work: {', '.join(f'`{item}`' for item in secrets)}."
            )

        entries.append(
            {
                "project_key": project["key"],
                "project_name": project["name"],
                "environment": project["environment"],
                "manifest_path": manifest["_path"],
                "targets": {
                    "runtime": targets["runtime_host"],
                    "ingress": targets["ingress_host"],
                    "data": targets["data_host"],
                },
                "enabled_services": enabled_services,
                "runtime_services": runtime_services,
                "shared_dependencies": shared_dependencies,
                "route_dependencies": route_dependencies,
                "secrets": secrets,
                "prerequisite_checks": prerequisite_checks,
            }
        )

    return entries, []


def _service_default_port(service_type: str) -> int | None:
    defaults = {
        "nextjs": 3000,
        "fastapi": 8000,
        "celery": None,
    }
    return defaults.get(service_type)


def _service_runtime_command(service_type: str) -> str:
    commands = {
        "nextjs": "npm run start",
        "fastapi": "uvicorn app.main:app --host 0.0.0.0 --port 8000",
        "celery": "celery -A app.worker worker --loglevel=info",
    }
    return commands.get(service_type, "run-the-service-entrypoint")


def _env_var_token(value: str) -> str:
    token = "".join(char if char.isalnum() else "_" for char in value.upper())
    return token.strip("_") or "SERVICE"


def _shared_dependency_env_contract(
    dependency: dict[str, Any],
    data_host: str,
    secrets: list[str],
) -> dict[str, Any]:
    dependency_type = dependency["type"]
    token = _env_var_token(dependency["name"])
    defaults: dict[str, dict[str, Any]] = {
        "postgres": {
            "non_secret_vars": ["POSTGRES_HOST", "POSTGRES_PORT"],
            "secret_vars": ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "DATABASE_URL"],
            "notes": "Prefer resolving database credentials or a composed connection string from Vaultwarden at runtime.",
        },
        "redis": {
            "non_secret_vars": ["REDIS_HOST", "REDIS_PORT"],
            "secret_vars": ["REDIS_URL"],
            "notes": "Keep any Redis auth or database-selection details in Vaultwarden-backed runtime config.",
        },
        "litellm": {
            "non_secret_vars": ["LITELLM_BASE_URL"],
            "secret_vars": [],
            "notes": "Point clients at the shared LiteLLM gateway on the data host.",
        },
        "langfuse": {
            "non_secret_vars": ["LANGFUSE_BASE_URL", "LANGFUSE_PUBLIC_KEY"],
            "secret_vars": ["LANGFUSE_SECRET_KEY"],
            "notes": "Expose the shared Langfuse endpoint and keep any secret key retrieval outside the repo.",
        },
        "otel": {
            "non_secret_vars": ["OTEL_EXPORTER_OTLP_ENDPOINT"],
            "secret_vars": [],
            "notes": "Use the shared OTLP collector endpoint for traces, logs, or metrics.",
        },
    }
    contract = defaults.get(
        dependency_type,
        {
            "non_secret_vars": [f"{token}_HOST"],
            "secret_vars": [],
            "notes": "Treat this shared service as an external attachment and bind concrete env vars in the project runtime repo.",
        },
    )
    return {
        "name": dependency["name"],
        "type": dependency_type,
        "host": data_host,
        "attachment_var": f"{token}_ATTACHMENT",
        "non_secret_vars": list(contract["non_secret_vars"]),
        "secret_vars": list(contract["secret_vars"]),
        "vaultwarden_refs": list(secrets) if contract["secret_vars"] else [],
        "notes": contract["notes"],
    }


def _build_env_contract_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    _, route_errors = _build_route_preview_entries(manifests)
    if route_errors:
        return entries, route_errors

    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        enabled_services = _build_enabled_services(manifest.get("services", {}))
        runtime_services = [service for service in enabled_services if not service["shared"]]
        shared_dependencies = [service for service in enabled_services if service["shared"]]
        routes = sorted(
            manifest.get("routes", []),
            key=lambda route: (route["service"], route["host"], route["port"]),
        )
        routes_by_service: dict[str, list[dict[str, Any]]] = {}
        for route in routes:
            routes_by_service.setdefault(route["service"], []).append(route)
        secrets = sorted(
            item
            for item in manifest.get("secrets", {}).get("vaultwarden_items", [])
            if isinstance(item, str) and item.strip()
        )
        dependency_contracts = [
            _shared_dependency_env_contract(dependency, targets["data_host"], secrets)
            for dependency in shared_dependencies
        ]
        attachment_vars = [dependency["attachment_var"] for dependency in dependency_contracts]
        dependency_secret_vars = sorted(
            {
                secret_var
                for dependency in dependency_contracts
                for secret_var in dependency["secret_vars"]
            }
        )
        runtime_contracts = []
        for service in runtime_services:
            service_routes = routes_by_service.get(service["name"], [])
            route_hosts = sorted({route["host"] for route in service_routes})
            route_ports = sorted({route["port"] for route in service_routes})
            default_port = _service_default_port(service["type"])
            expected_env_vars = ["PROJECT_KEY", "PROJECT_ENV"]
            if route_ports or default_port is not None:
                expected_env_vars.append("PORT")
            if route_hosts:
                expected_env_vars.append("PUBLIC_ROUTE_HOSTS")
            expected_env_vars.extend(attachment_vars)
            runtime_contracts.append(
                {
                    **service,
                    "route_hosts": route_hosts,
                    "route_ports": route_ports or ([default_port] if default_port is not None else []),
                    "expected_env_vars": expected_env_vars,
                    "attachment_vars": list(attachment_vars),
                    "secret_vars": list(dependency_secret_vars),
                    "vaultwarden_refs": list(secrets),
                }
            )
        entries.append(
            {
                "project_key": project["key"],
                "project_name": project["name"],
                "environment": project["environment"],
                "manifest_path": manifest["_path"],
                "targets": {
                    "runtime": targets["runtime_host"],
                    "ingress": targets["ingress_host"],
                    "data": targets["data_host"],
                },
                "runtime_contracts": runtime_contracts,
                "dependency_contracts": dependency_contracts,
                "vaultwarden_refs": secrets,
            }
        )

    return entries, []


def _build_runtime_skeleton_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    _, route_errors = _build_route_preview_entries(manifests)
    if route_errors:
        return entries, route_errors

    for manifest in manifests:
        project = manifest["project"]
        targets = manifest["targets"]
        enabled_services = _build_enabled_services(manifest.get("services", {}))
        runtime_services = [service for service in enabled_services if not service["shared"]]
        shared_dependencies = [service for service in enabled_services if service["shared"]]
        routes = sorted(
            manifest.get("routes", []),
            key=lambda route: (route["service"], route["host"], route["port"]),
        )
        routes_by_service: dict[str, list[dict[str, Any]]] = {}
        for route in routes:
            routes_by_service.setdefault(route["service"], []).append(route)
        secrets = sorted(
            item
            for item in manifest.get("secrets", {}).get("vaultwarden_items", [])
            if isinstance(item, str) and item.strip()
        )
        runtime_services_with_shape = []
        for service in runtime_services:
            service_routes = routes_by_service.get(service["name"], [])
            route_ports = sorted({route["port"] for route in service_routes})
            default_port = _service_default_port(service["type"])
            exposed_ports = route_ports or ([default_port] if default_port is not None else [])
            shared_attachment_names = [dependency["name"] for dependency in shared_dependencies]
            runtime_services_with_shape.append(
                {
                    **service,
                    "routes": service_routes,
                    "exposed_ports": exposed_ports,
                    "shared_attachment_names": shared_attachment_names,
                    "command": _service_runtime_command(service["type"]),
                }
            )
        entries.append(
            {
                "project_key": project["key"],
                "project_name": project["name"],
                "environment": project["environment"],
                "manifest_path": manifest["_path"],
                "targets": {
                    "runtime": targets["runtime_host"],
                    "ingress": targets["ingress_host"],
                    "data": targets["data_host"],
                },
                "runtime_services": runtime_services_with_shape,
                "shared_dependencies": shared_dependencies,
                "secrets": secrets,
            }
        )

    return entries, []


def _build_smoke_check_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    runtime_entries, errors = _build_runtime_skeleton_entries(manifests)
    if errors:
        return [], errors

    entries: list[dict[str, Any]] = []
    for entry in runtime_entries:
        routes = sorted(
            [
                {
                    "host": route["host"],
                    "service": service["name"],
                    "service_type": service["type"],
                    "port": route["port"],
                    "upstream": f"{entry['targets']['runtime']}:{route['port']}",
                }
                for service in entry["runtime_services"]
                for route in service["routes"]
            ],
            key=lambda route: (route["host"], route["service"], route["port"]),
        )
        runtime_service_names = [f"`{service['name']}`" for service in entry["runtime_services"]]
        route_targets = [
            f"`{route['host']}` -> `{route['upstream']}` via `{route['service']}`"
            for route in routes
        ]
        dependency_names = [f"`{dependency['name']}`" for dependency in entry["shared_dependencies"]]
        operator_checks = [
            (
                "Runtime services",
                f"Confirm runtime host `{entry['targets']['runtime']}` shows the planned workloads running: "
                f"{', '.join(runtime_service_names) if runtime_service_names else '`<none>`'}."
            ),
            (
                "Routes",
                f"Confirm ingress `{entry['targets']['ingress']}` presents the documented public routes after deployment: "
                f"{'; '.join(route_targets) if route_targets else '`<none>`'}."
            ),
            (
                "Shared dependencies",
                f"Confirm runtime services can reach shared dependencies on `{entry['targets']['data']}`: "
                f"{', '.join(dependency_names) if dependency_names else '`<none>`'}."
            ),
            (
                "Operator notes",
                "Capture observed results, regressions, and follow-up actions outside this generated artifact before any further rollout work.",
            ),
        ]
        entries.append(
            {
                **entry,
                "routes": routes,
                "operator_checks": operator_checks,
            }
        )

    return entries, []


def _build_handoff_packet_entries(manifests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    route_entries, route_errors = _build_route_preview_entries(manifests)
    if route_errors:
        return [], route_errors

    deploy_entries, deploy_errors = _build_deploy_plan_entries(manifests)
    if deploy_errors:
        return [], deploy_errors

    bootstrap_entries, bootstrap_errors = _build_bootstrap_checklist_entries(manifests)
    if bootstrap_errors:
        return [], bootstrap_errors

    runtime_entries, runtime_errors = _build_runtime_skeleton_entries(manifests)
    if runtime_errors:
        return [], runtime_errors

    env_entries, env_errors = _build_env_contract_entries(manifests)
    if env_errors:
        return [], env_errors

    smoke_entries, smoke_errors = _build_smoke_check_entries(manifests)
    if smoke_errors:
        return [], smoke_errors

    route_entries_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for entry in route_entries:
        key = (entry["project_key"], entry["environment"], entry["manifest_path"])
        route_entries_by_key.setdefault(key, []).append(entry)

    deploy_entries_by_key = {
        (entry["project_key"], entry["environment"], entry["manifest_path"]): entry
        for entry in deploy_entries
    }
    bootstrap_entries_by_key = {
        (entry["project_key"], entry["environment"], entry["manifest_path"]): entry
        for entry in bootstrap_entries
    }
    runtime_entries_by_key = {
        (entry["project_key"], entry["environment"], entry["manifest_path"]): entry
        for entry in runtime_entries
    }
    env_entries_by_key = {
        (entry["project_key"], entry["environment"], entry["manifest_path"]): entry
        for entry in env_entries
    }
    smoke_entries_by_key = {
        (entry["project_key"], entry["environment"], entry["manifest_path"]): entry
        for entry in smoke_entries
    }

    packet_entries: list[dict[str, Any]] = []
    for entry in deploy_entries:
        key = (entry["project_key"], entry["environment"], entry["manifest_path"])
        bootstrap_entry = bootstrap_entries_by_key.get(key)
        runtime_entry = runtime_entries_by_key.get(key)
        env_entry = env_entries_by_key.get(key)
        smoke_entry = smoke_entries_by_key.get(key)
        if bootstrap_entry is None or runtime_entry is None or env_entry is None or smoke_entry is None:
            return [], [f"internal handoff packet mismatch for `{entry['manifest_path']}`"]

        route_preview_entries = route_entries_by_key.get(key, [])
        exposed_ports = sorted(
            {
                port
                for service in runtime_entry["runtime_services"]
                for port in service["exposed_ports"]
            }
        )
        attachment_vars = sorted(
            {
                attachment_var
                for contract in env_entry["runtime_contracts"]
                for attachment_var in contract["attachment_vars"]
            }
        )
        secret_env_vars = sorted(
            {
                secret_var
                for contract in env_entry["dependency_contracts"]
                for secret_var in contract["secret_vars"]
            }
        )
        packet_entries.append(
            {
                "project_key": entry["project_key"],
                "project_name": entry["project_name"],
                "environment": entry["environment"],
                "manifest_path": entry["manifest_path"],
                "targets": dict(entry["targets"]),
                "route_preview": {
                    "artifact_path": "docs/runbooks/generated/project-route-preview.md",
                    "route_count": len(route_preview_entries),
                    "routes": [
                        f"`{item['host']}` -> `{item['upstream']}` via `{item['service']}`"
                        for item in route_preview_entries
                    ],
                },
                "deploy_plan": {
                    "artifact_path": "docs/runbooks/generated/project-deploy-plan.md",
                    "service_count": len(entry["enabled_services"]),
                    "route_count": len(entry["routes"]),
                    "secret_count": len(entry["secrets"]),
                    "operator_checkpoint_count": 5,
                },
                "bootstrap_checklist": {
                    "artifact_path": "docs/runbooks/generated/project-bootstrap-checklist.md",
                    "prerequisite_count": len(bootstrap_entry["prerequisite_checks"]),
                    "runtime_service_count": len(bootstrap_entry["runtime_services"]),
                    "shared_dependency_count": len(bootstrap_entry["shared_dependencies"]),
                    "approval_checkpoint_count": 6,
                },
                "runtime_skeleton": {
                    "artifact_path": "docs/runbooks/generated/project-runtime-skeleton.md",
                    "runtime_service_count": len(runtime_entry["runtime_services"]),
                    "shared_dependency_count": len(runtime_entry["shared_dependencies"]),
                    "exposed_ports": exposed_ports,
                },
                "env_contract": {
                    "artifact_path": "docs/runbooks/generated/project-env-contract.md",
                    "runtime_contract_count": len(env_entry["runtime_contracts"]),
                    "dependency_contract_count": len(env_entry["dependency_contracts"]),
                    "vaultwarden_ref_count": len(env_entry["vaultwarden_refs"]),
                    "attachment_vars": attachment_vars,
                    "secret_env_vars": secret_env_vars,
                },
                "smoke_check": {
                    "artifact_path": "docs/runbooks/generated/project-smoke-check.md",
                    "runtime_service_count": len(smoke_entry["runtime_services"]),
                    "route_count": len(smoke_entry["routes"]),
                    "shared_dependency_count": len(smoke_entry["shared_dependencies"]),
                    "operator_check_count": len(smoke_entry["operator_checks"]),
                },
            }
        )

    return packet_entries, []


def render_deploy_plan(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_deploy_plan_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project Deployment Plan",
        "",
        "Generated from validated project manifests under `projects/`.",
        "Planning only. This artifact does not provision hosts, deploy services, or change live routing.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No validated project manifests were found.",
                "",
                "Create manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py deploy-plan`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Runtime Host | Ingress Host | Data Host | Services | Routes | Secrets | Path |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| `{entry['project_key']}` | "
            f"`{entry['environment']}` | "
            f"`{entry['targets']['runtime']}` | "
            f"`{entry['targets']['ingress']}` | "
            f"`{entry['targets']['data']}` | "
            f"{len(entry['enabled_services'])} | "
            f"{len(entry['routes'])} | "
            f"{len(entry['secrets'])} | "
            f"`{entry['manifest_path']}` |"
        )
    lines.append("")

    for entry in entries:
        route_lines = [
            f"`{route['host']}` -> `{entry['targets']['runtime']}:{route['port']}`"
            f" via `{route['service']}`"
            for route in entry["routes"]
        ]
        service_names = [f"`{service['name']}`" for service in entry["enabled_services"]]
        lines.extend(
            [
                f"## {entry['project_name']}",
                "",
                f"- Key: `{entry['project_key']}`",
                f"- Environment: `{entry['environment']}`",
                f"- Manifest: `{entry['manifest_path']}`",
                "",
                "### Target Hosts",
                "",
                "| Role | Host |",
                "| --- | --- |",
                f"| Runtime | `{entry['targets']['runtime']}` |",
                f"| Ingress | `{entry['targets']['ingress']}` |",
                f"| Data | `{entry['targets']['data']}` |",
                "",
                "### Enabled Services",
                "",
                "| Service | Type | Shared | Notes |",
                "| --- | --- | --- | --- |",
            ]
        )
        for service in entry["enabled_services"]:
            notes = (
                "extensions: " + ", ".join(f"`{item}`" for item in service["extensions"])
                if service["extensions"]
                else "`<none>`"
            )
            lines.append(
                f"| `{service['name']}` | `{service['type']}` | "
                f"`{'yes' if service['shared'] else 'no'}` | {notes} |"
            )
        if not entry["enabled_services"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` |")
        lines.extend(
            [
                "",
                "### Routes",
                "",
                "| Host | Service | Port | Upstream |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for route in entry["routes"]:
            lines.append(
                f"| `{route['host']}` | `{route['service']}` | {route['port']} | "
                f"`{entry['targets']['runtime']}:{route['port']}` |"
            )
        if not entry["routes"]:
            lines.append("| `<none>` | `<none>` | 0 | `<none>` |")
        lines.extend(
            [
                "",
                "### Secrets References",
                "",
            ]
        )
        if entry["secrets"]:
            for secret in entry["secrets"]:
                lines.append(f"- `{secret}`")
        else:
            lines.append("- `<none>`")
        lines.extend(
            [
                "",
                "### Operator Checkpoints",
                "",
                f"- [ ] Confirm target hosts are ready: runtime `{entry['targets']['runtime']}`, ingress `{entry['targets']['ingress']}`, data `{entry['targets']['data']}`.",
                f"- [ ] Confirm enabled services are intended for this environment: {', '.join(service_names) if service_names else '`<none>`'}.",
                f"- [ ] Confirm planned routes match the manifest and remain planning-only: {'; '.join(route_lines) if route_lines else '`<none>`'}.",
                f"- [ ] Confirm Vaultwarden references exist before any manual deployment work: {', '.join(f'`{item}`' for item in entry['secrets']) if entry['secrets'] else '`<none>`'}.",
                "- [ ] Record operator approval and any follow-up execution notes outside this generated artifact before taking non-dry-run actions.",
                "",
            ]
        )
    return "\n".join(lines)


def render_bootstrap_checklist(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_bootstrap_checklist_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project Bootstrap Checklist",
        "",
        "Generated from validated project manifests under `projects/`.",
        "Planning only. This artifact does not bootstrap hosts, create compose files, or change live routing.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No validated project manifests were found.",
                "",
                "Create manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py bootstrap-checklist`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Target Runtime Host | Runtime Services | Shared Dependencies | Routes | Secrets | Path |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| `{entry['project_key']}` | "
            f"`{entry['environment']}` | "
            f"`{entry['targets']['runtime']}` | "
            f"{len(entry['runtime_services'])} | "
            f"{len(entry['shared_dependencies'])} | "
            f"{len(entry['route_dependencies'])} | "
            f"{len(entry['secrets'])} | "
            f"`{entry['manifest_path']}` |"
        )
    lines.append("")

    for entry in entries:
        runtime_service_names = [f"`{service['name']}`" for service in entry["runtime_services"]]
        shared_dependency_names = [f"`{service['name']}`" for service in entry["shared_dependencies"]]
        lines.extend(
            [
                f"## {entry['project_name']}",
                "",
                f"- Key: `{entry['project_key']}`",
                f"- Environment: `{entry['environment']}`",
                f"- Manifest: `{entry['manifest_path']}`",
                "",
                "### Target Runtime Host",
                "",
                "| Role | Host |",
                "| --- | --- |",
                f"| Runtime | `{entry['targets']['runtime']}` |",
                f"| Ingress Dependency | `{entry['targets']['ingress']}` |",
                f"| Data Dependency | `{entry['targets']['data']}` |",
                "",
                "### Required Runtime Prerequisites",
                "",
            ]
        )
        for item in entry["prerequisite_checks"]:
            lines.append(f"- [ ] {item}")
        lines.extend(
            [
                "",
                "### Services Requested",
                "",
                "| Service | Type | Shared | Placement | Notes |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for service in entry["enabled_services"]:
            placement = "`shared dependency`" if service["shared"] else "`runtime host`"
            notes = (
                "extensions: " + ", ".join(f"`{item}`" for item in service["extensions"])
                if service["extensions"]
                else "`<none>`"
            )
            lines.append(
                f"| `{service['name']}` | `{service['type']}` | "
                f"`{'yes' if service['shared'] else 'no'}` | {placement} | {notes} |"
            )
        if not entry["enabled_services"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` | `<none>` |")
        lines.extend(
            [
                "",
                "### Secret References",
                "",
            ]
        )
        if entry["secrets"]:
            for secret in entry["secrets"]:
                lines.append(f"- `{secret}`")
        else:
            lines.append("- `<none>`")
        lines.extend(
            [
                "",
                "### Route Dependencies",
                "",
                "| Public Host | Service | Port | Dependency |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for dependency in entry["route_dependencies"]:
            lines.append(
                f"| `{dependency['host']}` | `{dependency['service']}` | {dependency['port']} | "
                f"`{dependency['dependency']}` |"
            )
        if not entry["route_dependencies"]:
            lines.append("| `<none>` | `<none>` | 0 | `<none>` |")
        lines.extend(
            [
                "",
                "### Human Approval Checkpoints",
                "",
                f"- [ ] Approve `{entry['targets']['runtime']}` as the first single-VM runtime host for `{entry['project_key']}`.",
                f"- [ ] Approve requested runtime-host services: {', '.join(runtime_service_names) if runtime_service_names else '`<none>`'}.",
                f"- [ ] Approve shared service dependencies that must already exist: {', '.join(shared_dependency_names) if shared_dependency_names else '`<none>`'}.",
                f"- [ ] Approve route dependencies from ingress `{entry['targets']['ingress']}` into runtime `{entry['targets']['runtime']}` as documented above.",
                f"- [ ] Approve Vaultwarden secret references for manual retrieval only: {', '.join(f'`{item}`' for item in entry['secrets']) if entry['secrets'] else '`<none>`'}.",
                "- [ ] Record explicit human approval before any non-dry-run bootstrap or deployment action outside this generated artifact.",
                "",
            ]
        )
    return "\n".join(lines)


def render_runtime_skeleton(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_runtime_skeleton_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project Runtime Skeleton",
        "",
        "Generated from validated project manifests under `projects/`.",
        "Planning only. This artifact does not create compose bundles, deploy containers, or change live routing.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No validated project manifests were found.",
                "",
                "Create manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py runtime-skeleton`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Runtime Host | Runtime Services | Shared Dependencies | Secrets | Path |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| `{entry['project_key']}` | "
            f"`{entry['environment']}` | "
            f"`{entry['targets']['runtime']}` | "
            f"{len(entry['runtime_services'])} | "
            f"{len(entry['shared_dependencies'])} | "
            f"{len(entry['secrets'])} | "
            f"`{entry['manifest_path']}` |"
        )
    lines.append("")

    for entry in entries:
        lines.extend(
            [
                f"## {entry['project_name']}",
                "",
                f"- Key: `{entry['project_key']}`",
                f"- Environment: `{entry['environment']}`",
                f"- Manifest: `{entry['manifest_path']}`",
                "",
                "### Host Placement",
                "",
                "| Role | Host |",
                "| --- | --- |",
                f"| Runtime | `{entry['targets']['runtime']}` |",
                f"| Ingress Dependency | `{entry['targets']['ingress']}` |",
                f"| Data Dependency | `{entry['targets']['data']}` |",
                "",
                "### Runtime Services",
                "",
                "| Service | Type | Exposed Ports | Shared Attachments |",
                "| --- | --- | --- | --- |",
            ]
        )
        for service in entry["runtime_services"]:
            exposed_ports = ", ".join(f"`{port}`" for port in service["exposed_ports"]) if service["exposed_ports"] else "`<none>`"
            attachments = (
                ", ".join(f"`{name}`" for name in service["shared_attachment_names"])
                if service["shared_attachment_names"]
                else "`<none>`"
            )
            lines.append(
                f"| `{service['name']}` | `{service['type']}` | {exposed_ports} | {attachments} |"
            )
        if not entry["runtime_services"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Shared Dependency Attachments",
                "",
                "| Dependency | Type | Host | Notes |",
                "| --- | --- | --- | --- |",
            ]
        )
        for dependency in entry["shared_dependencies"]:
            notes = (
                "extensions: " + ", ".join(f"`{item}`" for item in dependency["extensions"])
                if dependency["extensions"]
                else "`shared service`"
            )
            lines.append(
                f"| `{dependency['name']}` | `{dependency['type']}` | `{entry['targets']['data']}` | {notes} |"
            )
        if not entry["shared_dependencies"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Planning Skeleton",
                "",
                "```yaml",
                "services:",
            ]
        )
        for service in entry["runtime_services"]:
            lines.append(f"  {service['name']}:")
            lines.append(f"    image: ghcr.io/example/{entry['project_key']}/{service['name']}:{entry['environment']}")
            lines.append(f"    command: {service['command']}")
            lines.append("    environment:")
            lines.append(f"      PROJECT_KEY: {entry['project_key']}")
            lines.append(f"      PROJECT_ENV: {entry['environment']}")
            if service["shared_attachment_names"]:
                for dependency_name in service["shared_attachment_names"]:
                    lines.append(
                        f"      {dependency_name.upper()}_ATTACHMENT: from-{entry['targets']['data']}"
                    )
            else:
                lines.append("      RUNTIME_MODE: standalone")
            if service["exposed_ports"]:
                lines.append("    expose:")
                for port in service["exposed_ports"]:
                    lines.append(f'      - "{port}"')
            if service["routes"]:
                lines.append("    labels:")
                for route in service["routes"]:
                    lines.append(f"      route.host: {route['host']}")
                    lines.append(f"      route.port: '{route['port']}'")
            lines.append("    # planning-only skeleton; refine in the project repo or deploy plan before execution")
        if not entry["runtime_services"]:
            lines.append("  {}")
        lines.extend(
            [
                "```",
                "",
                "### Secret References",
                "",
            ]
        )
        if entry["secrets"]:
            for secret in entry["secrets"]:
                lines.append(f"- `{secret}`")
        else:
            lines.append("- `<none>`")
        lines.extend(
            [
                "",
                "### Operator Notes",
                "",
                f"- Runtime skeleton host: `{entry['targets']['runtime']}`",
                f"- Shared dependencies stay off-host and should already exist on `{entry['targets']['data']}`.",
                "- Treat the YAML block above as a planning scaffold only. Final runtime definitions should live in project-specific deployment assets.",
                "",
            ]
        )
    return "\n".join(lines)


def render_env_contract(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_env_contract_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project Env Contract",
        "",
        "Generated from validated project manifests under `projects/`.",
        "Planning only. This artifact does not resolve Vaultwarden items, inject env values, or deploy services.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No validated project manifests were found.",
                "",
                "Create manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py env-contract`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Runtime Host | Runtime Services | Shared Dependencies | Vaultwarden Refs | Path |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| `{entry['project_key']}` | "
            f"`{entry['environment']}` | "
            f"`{entry['targets']['runtime']}` | "
            f"{len(entry['runtime_contracts'])} | "
            f"{len(entry['dependency_contracts'])} | "
            f"{len(entry['vaultwarden_refs'])} | "
            f"`{entry['manifest_path']}` |"
        )
    lines.append("")

    for entry in entries:
        lines.extend(
            [
                f"## {entry['project_name']}",
                "",
                f"- Key: `{entry['project_key']}`",
                f"- Environment: `{entry['environment']}`",
                f"- Manifest: `{entry['manifest_path']}`",
                f"- Runtime host: `{entry['targets']['runtime']}`",
                f"- Data dependency host: `{entry['targets']['data']}`",
                "",
                "### Vaultwarden Reference Set",
                "",
            ]
        )
        if entry["vaultwarden_refs"]:
            for ref_name in entry["vaultwarden_refs"]:
                lines.append(f"- `{ref_name}`")
        else:
            lines.append("- `<none>`")
        lines.extend(
            [
                "",
                "### Shared Dependency Contract",
                "",
                "| Dependency | Type | Attachment Var | Non-Secret Env Vars | Secret Env Vars | Vaultwarden Refs | Notes |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for dependency in entry["dependency_contracts"]:
            non_secret_vars = (
                ", ".join(f"`{item}`" for item in dependency["non_secret_vars"])
                if dependency["non_secret_vars"]
                else "`<none>`"
            )
            secret_vars = (
                ", ".join(f"`{item}`" for item in dependency["secret_vars"])
                if dependency["secret_vars"]
                else "`<none>`"
            )
            vaultwarden_refs = (
                ", ".join(f"`{item}`" for item in dependency["vaultwarden_refs"])
                if dependency["vaultwarden_refs"]
                else "`<none>`"
            )
            lines.append(
                f"| `{dependency['name']}` | `{dependency['type']}` | `{dependency['attachment_var']}` | "
                f"{non_secret_vars} | {secret_vars} | {vaultwarden_refs} | {dependency['notes']} |"
            )
        if not entry["dependency_contracts"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` | `<none>` | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Runtime Service Contract",
                "",
                "| Service | Type | Expected Env Vars | Shared Attachment Vars | Vaultwarden Usage |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for contract in entry["runtime_contracts"]:
            expected_vars = ", ".join(f"`{item}`" for item in contract["expected_env_vars"])
            attachment_vars = (
                ", ".join(f"`{item}`" for item in contract["attachment_vars"])
                if contract["attachment_vars"]
                else "`<none>`"
            )
            vaultwarden_usage = (
                "manual retrieval for "
                + ", ".join(f"`{item}`" for item in contract["vaultwarden_refs"])
                if contract["vaultwarden_refs"]
                else "`<none>`"
            )
            lines.append(
                f"| `{contract['name']}` | `{contract['type']}` | {expected_vars} | "
                f"{attachment_vars} | {vaultwarden_usage} |"
            )
        if not entry["runtime_contracts"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Planning Notes",
                "",
                "- Attachment vars above are deterministic planning placeholders only; bind concrete values in project-specific runtime assets later.",
                "- Secret values are intentionally omitted. Resolve only the listed Vaultwarden references during manual planning or future runtime implementation.",
                "- Use the shared dependency rows to translate attachment placeholders into concrete runtime vars such as `DATABASE_URL`, `REDIS_URL`, or `OTEL_EXPORTER_OTLP_ENDPOINT`.",
                "",
            ]
        )
    return "\n".join(lines)


def render_smoke_check(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_smoke_check_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project Smoke Check Contract",
        "",
        "Generated from validated project manifests under `projects/`.",
        "Planning only. This artifact does not execute live health checks, hit live routes, or change deployment state.",
        "Use it as a deterministic first-deployment checklist for what operators should verify after rollout.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No validated project manifests were found.",
                "",
                "Create manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py smoke-check`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Runtime Host | Runtime Services | Shared Dependencies | Routes | Operator Checks | Path |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| `{entry['project_key']}` | "
            f"`{entry['environment']}` | "
            f"`{entry['targets']['runtime']}` | "
            f"{len(entry['runtime_services'])} | "
            f"{len(entry['shared_dependencies'])} | "
            f"{len(entry['routes'])} | "
            f"{len(entry['operator_checks'])} | "
            f"`{entry['manifest_path']}` |"
        )
    lines.append("")

    for entry in entries:
        lines.extend(
            [
                f"## {entry['project_name']}",
                "",
                f"- Key: `{entry['project_key']}`",
                f"- Environment: `{entry['environment']}`",
                f"- Manifest: `{entry['manifest_path']}`",
                f"- Runtime host: `{entry['targets']['runtime']}`",
                f"- Ingress dependency: `{entry['targets']['ingress']}`",
                f"- Data dependency: `{entry['targets']['data']}`",
                "",
                "### Runtime Services To Verify",
                "",
                "| Service | Type | Planned Ports | Planned Verification |",
                "| --- | --- | --- | --- |",
            ]
        )
        for service in entry["runtime_services"]:
            ports = ", ".join(f"`{port}`" for port in service["exposed_ports"]) if service["exposed_ports"] else "`<none>`"
            if service["exposed_ports"]:
                verification = (
                    f"Confirm `{service['name']}` is visible on `{entry['targets']['runtime']}` and listening on "
                    f"{', '.join(f'`{port}`' for port in service['exposed_ports'])}."
                )
            else:
                verification = (
                    f"Confirm `{service['name']}` stays running on `{entry['targets']['runtime']}` and shows no immediate startup failures."
                )
            lines.append(
                f"| `{service['name']}` | `{service['type']}` | {ports} | {verification} |"
            )
        if not entry["runtime_services"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Routes To Verify",
                "",
                "| Host | Service | Port | Upstream | Planned Verification |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for route in entry["routes"]:
            lines.append(
                f"| `{route['host']}` | `{route['service']}` | {route['port']} | `{route['upstream']}` | "
                f"Confirm operators can observe the expected response for `{route['host']}` through ingress `{entry['targets']['ingress']}` after deployment. |"
            )
        if not entry["routes"]:
            lines.append("| `<none>` | `<none>` | 0 | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Shared Dependencies To Verify",
                "",
                "| Dependency | Type | Host | Planned Verification |",
                "| --- | --- | --- | --- |",
            ]
        )
        for dependency in entry["shared_dependencies"]:
            verification = f"Confirm `{dependency['name']}` remains reachable from `{entry['targets']['runtime']}` on `{entry['targets']['data']}`."
            if dependency["extensions"]:
                verification += " Required platform notes: " + ", ".join(
                    f"`{item}`" for item in dependency["extensions"]
                ) + "."
            lines.append(
                f"| `{dependency['name']}` | `{dependency['type']}` | `{entry['targets']['data']}` | {verification} |"
            )
        if not entry["shared_dependencies"]:
            lines.append("| `<none>` | `<none>` | `<none>` | `<none>` |")

        lines.extend(
            [
                "",
                "### Operator-Visible Checks",
                "",
            ]
        )
        for category, item in entry["operator_checks"]:
            lines.append(f"- [ ] {category}: {item}")
        lines.append("")
    return "\n".join(lines)


def render_handoff_packet(manifests: list[dict[str, Any]]) -> str:
    entries, errors = _build_handoff_packet_entries(manifests)
    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        "# Project Handoff Packet",
        "",
        "Generated from validated project manifests under `projects/`.",
        "Planning only. This artifact does not bootstrap hosts, deploy services, resolve secret values, or execute health checks.",
        "It summarizes the operator-facing planning artifacts that Cortex can already derive from the same validated manifests.",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "No validated project manifests were found.",
                "",
                "Create manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py handoff-packet`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Summary",
            "",
            "| Project | Environment | Runtime Host | Routes | Runtime Services | Shared Dependencies | Vaultwarden Refs | Path |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in entries:
        lines.append(
            f"| `{entry['project_key']}` | "
            f"`{entry['environment']}` | "
            f"`{entry['targets']['runtime']}` | "
            f"{entry['route_preview']['route_count']} | "
            f"{entry['runtime_skeleton']['runtime_service_count']} | "
            f"{entry['runtime_skeleton']['shared_dependency_count']} | "
            f"{entry['env_contract']['vaultwarden_ref_count']} | "
            f"`{entry['manifest_path']}` |"
        )
    lines.append("")

    for entry in entries:
        exposed_ports = (
            ", ".join(f"`{port}`" for port in entry["runtime_skeleton"]["exposed_ports"])
            if entry["runtime_skeleton"]["exposed_ports"]
            else "`<none>`"
        )
        attachment_vars = (
            ", ".join(f"`{item}`" for item in entry["env_contract"]["attachment_vars"])
            if entry["env_contract"]["attachment_vars"]
            else "`<none>`"
        )
        secret_env_vars = (
            ", ".join(f"`{item}`" for item in entry["env_contract"]["secret_env_vars"])
            if entry["env_contract"]["secret_env_vars"]
            else "`<none>`"
        )
        route_summary = (
            "; ".join(entry["route_preview"]["routes"])
            if entry["route_preview"]["routes"]
            else "`<none>`"
        )
        lines.extend(
            [
                f"## {entry['project_name']}",
                "",
                f"- Key: `{entry['project_key']}`",
                f"- Environment: `{entry['environment']}`",
                f"- Manifest: `{entry['manifest_path']}`",
                f"- Runtime host: `{entry['targets']['runtime']}`",
                f"- Ingress dependency: `{entry['targets']['ingress']}`",
                f"- Data dependency: `{entry['targets']['data']}`",
                "",
                "### Artifact References",
                "",
                "| Artifact | Generated Path | Operator Summary |",
                "| --- | --- | --- |",
                f"| Route preview | `{entry['route_preview']['artifact_path']}` | {entry['route_preview']['route_count']} route(s): {route_summary} |",
                f"| Deploy plan | `{entry['deploy_plan']['artifact_path']}` | {entry['deploy_plan']['service_count']} enabled service(s), {entry['deploy_plan']['route_count']} route(s), {entry['deploy_plan']['secret_count']} Vaultwarden reference(s), {entry['deploy_plan']['operator_checkpoint_count']} operator checkpoint(s). |",
                f"| Bootstrap checklist | `{entry['bootstrap_checklist']['artifact_path']}` | {entry['bootstrap_checklist']['prerequisite_count']} prerequisite check(s), {entry['bootstrap_checklist']['runtime_service_count']} runtime-host service(s), {entry['bootstrap_checklist']['shared_dependency_count']} shared dependency attachment(s), {entry['bootstrap_checklist']['approval_checkpoint_count']} approval checkpoint(s). |",
                f"| Runtime skeleton | `{entry['runtime_skeleton']['artifact_path']}` | {entry['runtime_skeleton']['runtime_service_count']} runtime service scaffold(s), {entry['runtime_skeleton']['shared_dependency_count']} shared dependency attachment(s), exposed planning ports {exposed_ports}. |",
                f"| Env contract | `{entry['env_contract']['artifact_path']}` | {entry['env_contract']['runtime_contract_count']} runtime contract(s), {entry['env_contract']['dependency_contract_count']} shared dependency contract(s), attachment vars {attachment_vars}, secret env vars {secret_env_vars}. |",
                f"| Smoke-check contract | `{entry['smoke_check']['artifact_path']}` | {entry['smoke_check']['runtime_service_count']} runtime verification target(s), {entry['smoke_check']['route_count']} route verification target(s), {entry['smoke_check']['shared_dependency_count']} shared dependency verification target(s), {entry['smoke_check']['operator_check_count']} operator-visible check(s). |",
                "",
                "### Operator Handoff Checklist",
                "",
                f"- [ ] Review route preview coverage for ingress `{entry['targets']['ingress']}` into runtime `{entry['targets']['runtime']}`: {route_summary}.",
                f"- [ ] Review deployment and bootstrap planning together for `{entry['project_key']}` before any manual execution work on `{entry['targets']['runtime']}`.",
                f"- [ ] Review runtime skeleton and env contract together so attachment placeholders stay aligned: {attachment_vars}.",
                f"- [ ] Review smoke-check expectations after any future rollout and record outcomes outside this generated packet; planned secret env vars remain documentation-only: {secret_env_vars}.",
                "",
            ]
        )
    return "\n".join(lines)


def cmd_validate(base_dir: Path, manifest_path: Path | None) -> int:
    if manifest_path is not None:
        try:
            payload = load_json(manifest_path)
        except Exception as exc:
            print(f"[FAIL] {manifest_path}: failed to parse JSON ({exc})")
            return 1
        errors = validate_manifest_payload(manifest_path, payload)
        if errors:
            for item in errors:
                print(f"[FAIL] {item}")
            return 1
        print(f"[PASS] {manifest_path}")
        return 0

    manifests, errors = load_validated_manifests(base_dir)
    for manifest in manifests:
        print(f"[PASS] {manifest['_path']}")
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1
    print(f"PROJECT-MANIFESTS: PASS ({len(manifests)} manifest(s))")
    return 0


def cmd_catalog(base_dir: Path, output: Path) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_catalog(manifests).rstrip() + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_route_preview(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, preview_errors = _build_route_preview_entries(manifests)
    if preview_errors:
        for item in preview_errors:
            print(f"[FAIL] {item}")
        return 1

    if output is None:
        print(render_caddy_route_preview(manifests).rstrip())
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_route_preview_doc(manifests).rstrip() + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_deploy_plan(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, plan_errors = _build_deploy_plan_entries(manifests)
    if plan_errors:
        for item in plan_errors:
            print(f"[FAIL] {item}")
        return 1

    rendered = render_deploy_plan(manifests).rstrip()
    if output is None:
        print(rendered)
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_bootstrap_checklist(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, checklist_errors = _build_bootstrap_checklist_entries(manifests)
    if checklist_errors:
        for item in checklist_errors:
            print(f"[FAIL] {item}")
        return 1

    rendered = render_bootstrap_checklist(manifests).rstrip()
    if output is None:
        print(rendered)
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_runtime_skeleton(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, skeleton_errors = _build_runtime_skeleton_entries(manifests)
    if skeleton_errors:
        for item in skeleton_errors:
            print(f"[FAIL] {item}")
        return 1

    rendered = render_runtime_skeleton(manifests).rstrip()
    if output is None:
        print(rendered)
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_env_contract(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, contract_errors = _build_env_contract_entries(manifests)
    if contract_errors:
        for item in contract_errors:
            print(f"[FAIL] {item}")
        return 1

    rendered = render_env_contract(manifests).rstrip()
    if output is None:
        print(rendered)
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_smoke_check(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, smoke_errors = _build_smoke_check_entries(manifests)
    if smoke_errors:
        for item in smoke_errors:
            print(f"[FAIL] {item}")
        return 1

    rendered = render_smoke_check(manifests).rstrip()
    if output is None:
        print(rendered)
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def cmd_handoff_packet(base_dir: Path, output: Path | None) -> int:
    manifests, errors = load_validated_manifests(base_dir)
    if errors:
        for item in errors:
            print(f"[FAIL] {item}")
        return 1

    _, packet_errors = _build_handoff_packet_entries(manifests)
    if packet_errors:
        for item in packet_errors:
            print(f"[FAIL] {item}")
        return 1

    rendered = render_handoff_packet(manifests).rstrip()
    if output is None:
        print(rendered)
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project manifest validation and docs generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate one manifest or all manifests")
    validate_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    validate_parser.add_argument("--manifest", help="Specific manifest file path")

    catalog_parser = subparsers.add_parser("catalog", help="Render project catalog markdown")
    catalog_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    catalog_parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output markdown path")

    route_preview_parser = subparsers.add_parser(
        "route-preview",
        help="Render preview Caddy routes from validated manifests",
    )
    route_preview_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    route_preview_parser.add_argument(
        "--output",
        default=str(DEFAULT_ROUTE_PREVIEW_OUTPUT),
        help="Output markdown path, or `-` to print raw Caddy output to stdout",
    )

    deploy_plan_parser = subparsers.add_parser(
        "deploy-plan",
        help="Render a planning-only deployment plan from validated manifests",
    )
    deploy_plan_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    deploy_plan_parser.add_argument(
        "--output",
        default=str(DEFAULT_DEPLOY_PLAN_OUTPUT),
        help="Output markdown path, or `-` to print the plan to stdout",
    )

    bootstrap_checklist_parser = subparsers.add_parser(
        "bootstrap-checklist",
        help="Render a planning-only bootstrap checklist from validated manifests",
    )
    bootstrap_checklist_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    bootstrap_checklist_parser.add_argument(
        "--output",
        default=str(DEFAULT_BOOTSTRAP_CHECKLIST_OUTPUT),
        help="Output markdown path, or `-` to print the checklist to stdout",
    )

    runtime_skeleton_parser = subparsers.add_parser(
        "runtime-skeleton",
        help="Render a planning-only runtime skeleton from validated manifests",
    )
    runtime_skeleton_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    runtime_skeleton_parser.add_argument(
        "--output",
        default=str(DEFAULT_RUNTIME_SKELETON_OUTPUT),
        help="Output markdown path, or `-` to print the runtime skeleton to stdout",
    )
    env_contract_parser = subparsers.add_parser(
        "env-contract",
        help="Render a planning-only environment and secret contract from validated manifests",
    )
    env_contract_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    env_contract_parser.add_argument(
        "--output",
        default=str(DEFAULT_ENV_CONTRACT_OUTPUT),
        help="Output markdown path, or `-` to print the env contract to stdout",
    )
    smoke_check_parser = subparsers.add_parser(
        "smoke-check",
        help="Render a planning-only first-deployment smoke-check contract from validated manifests",
    )
    smoke_check_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    smoke_check_parser.add_argument(
        "--output",
        default=str(DEFAULT_SMOKE_CHECK_OUTPUT),
        help="Output markdown path, or `-` to print the smoke-check contract to stdout",
    )
    handoff_packet_parser = subparsers.add_parser(
        "handoff-packet",
        help="Render a planning-only operator handoff packet from validated manifests",
    )
    handoff_packet_parser.add_argument("--dir", default=str(PROJECTS_DIR), help="Manifest directory")
    handoff_packet_parser.add_argument(
        "--output",
        default=str(DEFAULT_HANDOFF_PACKET_OUTPUT),
        help="Output markdown path, or `-` to print the handoff packet to stdout",
    )

    args = parser.parse_args(argv)
    base_dir = Path(args.dir).expanduser()
    if not base_dir.is_absolute():
        base_dir = REPO_ROOT / base_dir

    if args.command == "validate":
        manifest_path = None
        if args.manifest:
            manifest_path = Path(args.manifest).expanduser()
            if not manifest_path.is_absolute():
                manifest_path = REPO_ROOT / manifest_path
        return cmd_validate(base_dir, manifest_path)

    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = REPO_ROOT / output
    if args.command == "catalog":
        return cmd_catalog(base_dir, output)

    route_output: Path | None = None
    if args.output != "-":
        route_output = output
    if args.command == "route-preview":
        return cmd_route_preview(base_dir, route_output)
    if args.command == "deploy-plan":
        return cmd_deploy_plan(base_dir, route_output)
    if args.command == "bootstrap-checklist":
        return cmd_bootstrap_checklist(base_dir, route_output)
    if args.command == "runtime-skeleton":
        return cmd_runtime_skeleton(base_dir, route_output)
    if args.command == "env-contract":
        return cmd_env_contract(base_dir, route_output)
    if args.command == "smoke-check":
        return cmd_smoke_check(base_dir, route_output)
    return cmd_handoff_packet(base_dir, route_output)


if __name__ == "__main__":
    sys.exit(main())
