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
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp'
};

const dashboardAssets = new Set([
  'phase-archive.css', 'phase-signatures.css', 'phase-responsive.css',
  'phase-hero-scenes.css', 'glass-ui.css', 'phase-personalization.css',
  'phase-editorial-media.css', 'phase-taxonomy.js', 'phase-visuals.js',
  'phase-data.js', 'phase-runtime.js', 'phase-signatures.js', 'tesla-mobile.js',
  'phase-hero-fix.js', 'phase10r-archive.js', 'phase-hero-scenes.js',
  'aegis-current.js', 'phase-personalization.js', 'phase-editorial-media.js'
]);

const deployAssets = new Set([
  'aegisland.css', 'signature.css', 'research-home.css', 'research-media.css', 'phase-polish.css',
  'phase-polish-fixes.css', 'phase-polish-v2.css', 'phase-ui-consistency.css', 'final-convergence.css', 'craft-polish.css', 'frozen-lineage.js',
  'research-workspace.css', 'research-workspace.js'
]);

const sendFile = async (res, file) => {
  try {
    const body = await fs.readFile(file);
    res.writeHead(200, {
      'content-type': types[path.extname(file).toLowerCase()] || 'application/octet-stream',
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

  // Mirror deploy/vercel/vercel.json: the frozen evidence layer must win before
  // the generic historical phase route.
  if (/^\/phases\/phase(?:12|13a|13b|13c|1[4-9]|2[0-2])\/?$/i.test(p)) {
    return sendFile(res, path.join(dashboardRoot, 'phases', 'frozen.html'));
  }
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
  if (p.startsWith('/media/')) {
    const relative = p.slice('/media/'.length);
    if (!relative.includes('..') && !relative.includes('/')) return sendFile(res, path.join(deployRoot, 'media', relative));
  }

  const asset = p.replace(/^\//, '');
  if (deployAssets.has(asset)) return sendFile(res, path.join(deployRoot, asset));
  if (dashboardAssets.has(asset)) return sendFile(res, path.join(dashboardRoot, asset));
  if (p === '/favicon.svg' || p === '/favicon.ico') return sendFile(res, path.join(deployRoot, 'favicon.svg'));
  if (p === '/' || p === '/index.html') return sendFile(res, path.join(deployRoot, 'index.html'));

  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('Not found');
});

server.listen(port, '127.0.0.1', () => console.log(`local-vercel-server listening on http://127.0.0.1:${port}`));