#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`missing required env: ${name}`);
  }
  return value;
}

function expectedMonitorNames() {
  return [
    "Wiki (local)",
    "Vaultwarden (public)",
    "MinIO (public)",
    "Caddy Manager (LAN)",
  ];
}

function parseArgs(argv) {
  const options = { json: false, output: null };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--json") {
      options.json = true;
    } else if (argv[i] === "--output") {
      options.output = argv[i + 1] || null;
      i += 1;
    }
  }
  return options;
}

function buildSnapshot(baseUrl, results) {
  return {
    generated_at: new Date().toISOString(),
    source: "uptime-kuma",
    base_url: baseUrl,
    monitors: results,
  };
}

function writeSnapshot(outputPath, snapshot) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(snapshot, null, 2)}\n`, "utf8");
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
  const options = parseArgs(process.argv.slice(2));
  const baseUrl = requiredEnv("UPTIME_KUMA_BASE_URL");
  const username = requiredEnv("UPTIME_KUMA_USERNAME");
  const password = requiredEnv("UPTIME_KUMA_PASSWORD");
  const expected = expectedMonitorNames();

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
    const monitors = Object.values(monitorList || {}).filter((item) => item && item.name);

    const results = [];
    let missing = 0;
    for (const name of expected) {
      const monitor = monitors.find((item) => item.name === name);
      if (monitor) {
        console.log(`[OK] ${name}`);
        results.push({
          name,
          present: true,
          active: Boolean(monitor.active),
          status: typeof monitor.status === "number" ? monitor.status : null,
          url: monitor.url || "",
        });
      } else {
        console.log(`[MISSING] ${name}`);
        results.push({
          name,
          present: false,
          active: false,
          status: null,
          url: "",
        });
        missing += 1;
      }
    }

    const snapshot = buildSnapshot(baseUrl, results);
    if (options.output) {
      writeSnapshot(options.output, snapshot);
      console.log(`[INFO] wrote ${options.output}`);
    }
    if (options.json) {
      console.log(JSON.stringify(snapshot, null, 2));
    }

    if (missing > 0) {
      console.error(`UPTIME-KUMA-VERIFY: FAIL missing=${missing}`);
      process.exitCode = 1;
      return;
    }

    console.log("UPTIME-KUMA-VERIFY: PASS");
  } finally {
    socket.close();
  }
}

main().catch((error) => {
  console.error(`UPTIME-KUMA-VERIFY: FAIL ${error.message}`);
  process.exit(1);
});
