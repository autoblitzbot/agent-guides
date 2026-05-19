#!/usr/bin/env node

import http from "node:http";
import net from "node:net";

const listenHost = process.env.LISTEN_HOST;
const listenPort = Number(process.env.LISTEN_PORT);
const targetHost = process.env.TARGET_HOST || "127.0.0.1";
const targetPort = Number(process.env.TARGET_PORT);
const targetHostHeader = process.env.TARGET_HOST_HEADER || `${targetHost}:${targetPort}`;

if (!listenHost || !listenPort || !targetPort) {
  console.error("Set LISTEN_HOST, LISTEN_PORT, and TARGET_PORT.");
  process.exit(2);
}

function targetHeaders(headers) {
  return {
    ...headers,
    host: targetHostHeader,
  };
}

const server = http.createServer((req, res) => {
  const upstream = http.request({
    host: targetHost,
    port: targetPort,
    method: req.method,
    path: req.url,
    headers: targetHeaders(req.headers),
  }, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
    upstreamRes.pipe(res);
  });

  upstream.on("error", (error) => {
    res.writeHead(502, { "content-type": "text/plain" });
    res.end(`Upstream error: ${error.message}\n`);
  });

  req.pipe(upstream);
});

server.on("upgrade", (req, socket, head) => {
  const upstream = net.connect(targetPort, targetHost, () => {
    upstream.write(`${req.method} ${req.url} HTTP/${req.httpVersion}\r\n`);
    const headers = targetHeaders(req.headers);
    for (const [name, value] of Object.entries(headers)) {
      if (Array.isArray(value)) {
        for (const item of value) upstream.write(`${name}: ${item}\r\n`);
      } else if (value !== undefined) {
        upstream.write(`${name}: ${value}\r\n`);
      }
    }
    upstream.write("\r\n");
    if (head.length) upstream.write(head);
    socket.pipe(upstream);
    upstream.pipe(socket);
  });

  const closeBoth = () => {
    socket.destroy();
    upstream.destroy();
  };
  socket.on("error", closeBoth);
  upstream.on("error", closeBoth);
});

server.on("error", (error) => {
  console.error(error);
  process.exit(1);
});

server.listen(listenPort, listenHost, () => {
  console.log(`Proxying http://${listenHost}:${listenPort} -> http://${targetHostHeader}`);
});
