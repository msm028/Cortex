# Hosted Ops Status Refresh

## Purpose

Keep the hosted wiki `Ops Status` page current on `cortex-control` without manual rebuilds.

The refresh flow does four things on the control-plane host:

- verifies the Uptime Kuma baseline monitors
- writes `artifacts/status/uptime-kuma-live.json`
- regenerates `artifacts/generated/ops-status.md`
- rebuilds the hosted wiki with that generated overlay, without mutating tracked `docs/ops-status.md`

Because live ops status is generated on the host, use the deployed-checkout sync wrapper from [Git And Host File Management Policy](./git-and-host-management.md) when updating `/opt/cortex`.

## Files

- Script: `ops/bin/refresh_hosted_ops_status.sh`
- Service: `bootstrap/systemd/cortex-ops-status-refresh.service`
- Timer: `bootstrap/systemd/cortex-ops-status-refresh.timer`
- Host env file: `/etc/cortex/uptime-kuma.env`

## Host Prerequisites

Create the env file on `cortex-control` with root-only permissions:

```bash
sudo mkdir -p /etc/cortex
sudo chmod 700 /etc/cortex
sudo sh -c 'cat >/etc/cortex/uptime-kuma.env'
```

Contents:

```env
UPTIME_KUMA_BASE_URL=http://127.0.0.1:3001
UPTIME_KUMA_USERNAME=...
UPTIME_KUMA_PASSWORD=...
```

Lock it down:

```bash
sudo chmod 600 /etc/cortex/uptime-kuma.env
sudo chown root:root /etc/cortex/uptime-kuma.env
```

## Install

From `cortex-control`:

```bash
cd /opt/cortex
sudo install -m 0644 bootstrap/systemd/cortex-ops-status-refresh.service /etc/systemd/system/cortex-ops-status-refresh.service
sudo install -m 0644 bootstrap/systemd/cortex-ops-status-refresh.timer /etc/systemd/system/cortex-ops-status-refresh.timer
sudo systemctl daemon-reload
sudo systemctl enable --now cortex-ops-status-refresh.timer
```

## Manual Run

Force one refresh immediately:

```bash
cd /opt/cortex
sudo systemctl start cortex-ops-status-refresh.service
sudo systemctl status --no-pager cortex-ops-status-refresh.service
```

Expected result:

- `HOSTED-OPS-STATUS-REFRESH: PASS`

## Verify

Check timer state:

```bash
sudo systemctl list-timers --all | grep cortex-ops-status-refresh
sudo systemctl status --no-pager cortex-ops-status-refresh.timer
```

Check the hosted page:

```bash
curl -fsS http://127.0.0.1:8085/ops-status/ >/dev/null && echo "OPS-STATUS: PASS"
```

## Logs

```bash
sudo journalctl -u cortex-ops-status-refresh.service -n 100 --no-pager
sudo journalctl -u cortex-ops-status-refresh.timer -n 50 --no-pager
```

## Rollback

Disable the timer and remove the unit files:

```bash
sudo systemctl disable --now cortex-ops-status-refresh.timer
sudo rm -f /etc/systemd/system/cortex-ops-status-refresh.timer
sudo rm -f /etc/systemd/system/cortex-ops-status-refresh.service
sudo systemctl daemon-reload
```

This does not remove:

- `artifacts/status/uptime-kuma-live.json`
- `artifacts/generated/ops-status.md`
- the hosted wiki stack
