#!/usr/bin/env node
"use strict";

const DEFAULT_INTERVAL = 60;

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`missing required env: ${name}`);
  }
  return value;
}

function buildMonitors() {
  return [
    {
      name: "Wiki (local)",
      type: "http",
      url: "http://127.0.0.1:8085/",
      method: "GET",
      interval: DEFAULT_INTERVAL,
      retryInterval: DEFAULT_INTERVAL,
      resendInterval: 0,
      maxretries: 0,
      active: true,
      accepted_statuscodes: ["200-399"],
      kafkaProducerBrokers: [],
      kafkaProducerSaslOptions: [],
      notificationIDList: {},
    },
    {
      name: "Vaultwarden (public)",
      type: "http",
      url: "http://vault.thecortexstack.com",
      method: "GET",
      interval: DEFAULT_INTERVAL,
      retryInterval: DEFAULT_INTERVAL,
      resendInterval: 0,
      maxretries: 0,
      active: true,
      accepted_statuscodes: ["200-399"],
      kafkaProducerBrokers: [],
      kafkaProducerSaslOptions: [],
      notificationIDList: {},
    },
    {
      name: "MinIO (public)",
      type: "http",
      url: "http://minio.thecortexstack.com",
      method: "GET",
      interval: DEFAULT_INTERVAL,
      retryInterval: DEFAULT_INTERVAL,
      resendInterval: 0,
      maxretries: 0,
      active: true,
      accepted_statuscodes: ["200-399"],
      kafkaProducerBrokers: [],
      kafkaProducerSaslOptions: [],
      notificationIDList: {},
    },
    {
      name: "Caddy Manager (LAN)",
      type: "http",
      url: "http://192.168.1.124:8086/",
      method: "GET",
      interval: DEFAULT_INTERVAL,
      retryInterval: DEFAULT_INTERVAL,
      resendInterval: 0,
      maxretries: 0,
      active: true,
      accepted_statuscodes: ["200-399"],
      kafkaProducerBrokers: [],
      kafkaProducerSaslOptions: [],
      notificationIDList: {},
    },
  ];
}

function emitAck(socket, eventName, payload) {
  return new Promise((resolve) => {
    socket.emit(eventName, payload, (res) => resolve(res));
  });
}

function waitForEvent(socket, eventName, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timed out waiting for ${eventName}`)), timeoutMs);
    socket.once(eventName, (payload) => {
      clearTimeout(timer);
      resolve(payload);
    });
  });
}

async function main() {
  const dryRun = process.argv.includes("--dry-run");
  const baseUrl = requiredEnv("UPTIME_KUMA_BASE_URL");
  const username = requiredEnv("UPTIME_KUMA_USERNAME");
  const password = requiredEnv("UPTIME_KUMA_PASSWORD");
  const monitors = buildMonitors();

  if (dryRun) {
    console.log(JSON.stringify({ baseUrl, monitorNames: monitors.map((item) => item.name) }, null, 2));
    return;
  }

  const { io } = require("socket.io-client");
  const socket = io(baseUrl, {
    transports: ["websocket"],
    timeout: 10000,
    reconnection: false,
  });

  try {
    await new Promise((resolve, reject) => {
      socket.once("connect", resolve);
      socket.once("connect_error", reject);
    });

    const login = await emitAck(socket, "login", { username, password });
    if (!login || !login.ok) {
      throw new Error(`login failed: ${login && login.msg ? login.msg : "unknown error"}`);
    }

    const monitorList = await waitForEvent(socket, "monitorList", 10000);
    const existing = new Set(
      Object.values(monitorList || {})
        .map((item) => (item && item.name ? String(item.name) : ""))
        .filter(Boolean),
    );

    for (const monitor of monitors) {
      if (existing.has(monitor.name)) {
        console.log(`[SKIP] ${monitor.name}`);
        continue;
      }
      const result = await emitAck(socket, "add", monitor);
      if (!result || !result.ok) {
        throw new Error(`failed to add ${monitor.name}: ${result && result.msg ? result.msg : "unknown error"}`);
      }
      console.log(`[ADD] ${monitor.name} monitor_id=${result.monitorID}`);
    }

    console.log("UPTIME-KUMA-SEED: PASS");
  } finally {
    socket.close();
  }
}

main().catch((error) => {
  console.error(`UPTIME-KUMA-SEED: FAIL ${error.message}`);
  process.exit(1);
});
