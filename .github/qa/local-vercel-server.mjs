import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';

const deployRoot = path.resolve('deploy/vercel');
const dashboardRoot = path.resolve('dashboard');
const port = Number(process.env.PORT || 4173);

const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const dashboardAssets = new Set([
  'phase-archive.css', 'phase-signatures.css', 'phase-responsive.css',
  'phase-hero-scenes.css', 'glass-ui.css', 'phase-data.js', 'phase-runtime.js',
  'phase-signatures.js', 'tesla-mobile.js', 'phase-hero-fix.js',
  'phase10r-archive.js', 'phase-hero-scenes.js', 'aegis-current.js'
]);

const sendFile = async (res, file) => {
  try {
    const body = await fs.readFile(file);
    res.writeHead(200, {
      'content-type': types[path.extname(file)] || 'application/octet-stream',
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff'
    });
    res.end(body);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Not found');
  }
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || `127.0.0.1:${port}`}`);
  const p = url.pathname;

  if (p === '/phases/phase11' || p === '/phases/phase11/') {
    return sendFile(res, path.join(deployRoot, 'phase11.html'));
  }
  if (p === '/phases' || p === '/phases/') {
    return sendFile(res, path.join(dashboardRoot, 'phases', 'index.html'));
  }
  if (/^\/phases\/phase[^/]+\/?$/.test(p)) {
    return sendFile(res, path.join(dashboardRoot, 'phases', 'phase.html'));
  }
  if (p.startsWith('/dashboard/')) {
    const relative = p.slice('/dashboard/'.length);
    if (!relative.includes('..')) return sendFile(res, path.join(dashboardRoot, relative));
  }

  const asset = p.replace(/^\//, '');
  if (dashboardAssets.has(asset)) return sendFile(res, path.join(dashboardRoot, asset));
  if (p === '/favicon.svg' || p === '/favicon.ico') return sendFile(res, path.join(deployRoot, p === '/favicon.ico' ? 'favicon.svg' : 'favicon.svg'));
  if (p === '/' || p === '/index.html') return sendFile(res, path.join(deployRoot, 'index.html'));

  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('Not found');
});

server.listen(port, '127.0.0.1', () => console.log(`local-vercel-server listening on http://127.0.0.1:${port}`));
