import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve('deploy/vercel');
const port = Number(process.env.PORT || 4173);

const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const sendFile = async (res, file) => {
  try {
    const body = await fs.readFile(file);
    res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
    res.end(body);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Not found');
  }
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || `127.0.0.1:${port}`}`);
  const p = url.pathname;
  if (p === '/phases/phase11' || p === '/phases/phase11/') return sendFile(res, path.join(root, 'phase11.html'));
  if (p === '/tesla-strict.css') return sendFile(res, path.join(root, 'tesla-strict.css'));
  if (p === '/favicon.svg') return sendFile(res, path.join(root, 'favicon.svg'));
  if (p === '/favicon.ico') return sendFile(res, path.join(root, 'favicon.ico'));
  return sendFile(res, path.join(root, 'index.html'));
});

server.listen(port, '127.0.0.1', () => console.log(`local-vercel-server listening on http://127.0.0.1:${port}`));
