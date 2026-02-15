# Bitwarden CLI Onboarding

## Install Options (Ubuntu 22.04)

Snap:

```bash
sudo snap install bw
```

NPM:

```bash
npm install -g @bitwarden/cli
```

Note: on Linux, `build-essential` may be required for global npm installs in some environments.

Native executable:

1. Download the Linux x64 Bitwarden CLI bundle from the official release page.
2. Extract and mark executable:
   - `chmod +x bw`
3. Move into PATH:
   - `sudo mv bw /usr/local/bin/bw`

## Point CLI at Self-Hosted Server

```bash
bw logout
bw config server https://vault.<PUBLIC_DOMAIN>
```

Example:

```bash
bw config server https://vault.thecortexstack.com
```

## Login and Unlock Patterns

```bash
bw login
bw unlock --raw
```

Export the returned unlock value as `BW_SESSION` in the current shell only.

Do not commit tokens or secrets to repository files.
