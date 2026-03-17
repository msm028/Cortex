# Project Route Preview

Generated from validated project manifests under `projects/`.
This artifact is preview-only and does not update live routing.
Edit manifests in `projects/` and rerun `python3 ops/bin/project_manifest.py route-preview`.

```caddyfile
# Project manifest Caddy route preview
# Generated from validated manifests under `projects/`.
# Preview only. This file does not change live routing.

# Sample App (dev)
# Manifest: projects/examples/sample-app.json
api.sample-app.thecortexstack.com {
	# service: backend (fastapi)
	reverse_proxy sample-app-dev:8000
}
app.sample-app.thecortexstack.com {
	# service: frontend (nextjs)
	reverse_proxy sample-app-dev:3000
}
```
