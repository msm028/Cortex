#!/usr/bin/env node
"use strict";

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
    const existing = new Set(
      Object.values(monitorList || {})
        .map((item) => (item && item.name ? String(item.name) : ""))
        .filter(Boolean),
    );

    let missing = 0;
    for (const name of expected) {
      if (existing.has(name)) {
        console.log(`[OK] ${name}`);
      } else {
        console.log(`[MISSING] ${name}`);
        missing += 1;
      }
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
