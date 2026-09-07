import fs from 'node:fs/promises';
import path from 'node:path';

const outputDir = path.resolve(process.env.AEGIS_EDITORIAL_MEDIA_DIR || 'deploy/vercel/media');

const commonsRedirect = (title) =>
  `https://commons.wikimedia.org/wiki/Special:Redirect/file/${encodeURIComponent(title)}?width=1280`;

const nasaOriginal = (id) =>
  `https://images-assets.nasa.gov/image/${id}/${id}~orig.jpg`;

const acero = (file, id, label) => ({
  file,
  label,
  urls: [
    commonsRedirect(`Advanced Capabilities for Emergency Response Operations (ACERO) (${id}).jpg`),
    nasaOriginal(id)
  ]
});

const stereo = (file, id, label) => ({
  file,
  label,
  urls: [
    commonsRedirect(`STEReO Field Testing (${id}).jpg`),
    nasaOriginal(id)
  ]
});

// One distinct, real NASA photograph per published phase. Four of these are also
// reused sparingly on the homepage so the site does not download duplicate files.
const assets = [
  acero('phase01-context.jpg', 'ACD24-0180-005', 'Phase 1 supervised launch context'),
  acero('phase02-context.jpg', 'ACD24-0180-034', 'Phase 2 sustained-flight context'),
  acero('acero-ground-control.jpg', 'ACD24-0180-009', 'Phase 3 ground-control context'),
  acero('phase04-context.jpg', 'ACD24-0180-012', 'Phase 4 provenance context'),
  acero('phase05-context.jpg', 'ACD24-0180-001', 'Phase 5 field-stress context'),
  acero('acero-uav-flight.jpg', 'ACD24-0180-035', 'Phase 6 camera-payload flight context'),
  acero('phase06b-context.jpg', 'ACD24-0180-036', 'Phase 6B terminal-landing context'),
  stereo('phase07-context.jpg', 'NHQ202105050027', 'Phase 7 field-realism context'),
  stereo('phase08-context.jpg', 'NHQ202105050015', 'Phase 8 simulated-operations context'),
  acero('acero-uav-landing.jpg', 'ACD24-0180-037', 'Phase 9 landing-geometry context'),
  stereo('phase10-context.jpg', 'NHQ202105050020', 'Phase 10 monitored-operations context'),
  stereo('phase10r-context.jpg', 'NHQ202105050025', 'Phase 10R environmental-shift context'),
  stereo('stereo-uav-preflight.jpg', 'NHQ202105050002', 'Phase 11 pre-flight context'),
  acero('phase12-context.jpg', 'ACD24-0180-016', 'Phase 12 baseline context'),
  stereo('phase13a-context.jpg', 'NHQ202105050026', 'Phase 13A external-validity context'),
  acero('phase13b-context.jpg', 'ACD24-0180-022', 'Phase 13B paired-degradation context'),
  acero('phase13c-context.jpg', 'ACD24-0180-023', 'Phase 13C attribution context'),
  acero('phase14-context.jpg', 'ACD24-0180-021', 'Phase 14 bounded-test context'),
  acero('phase15-context.jpg', 'ACD24-0180-002', 'Phase 15 feasibility context'),
  acero('phase16-context.jpg', 'ACD24-0180-003', 'Phase 16 staleness context'),
  acero('phase17-context.jpg', 'ACD24-0180-004', 'Phase 17 context-mismatch context'),
  acero('phase18-context.jpg', 'ACD24-0180-038', 'Phase 18 protected-confirmation context'),
  acero('phase19-context.jpg', 'ACD24-0180-006', 'Phase 19 residual-effect context'),
  acero('phase20-context.jpg', 'ACD24-0180-029', 'Phase 20 factor-decomposition context'),
  acero('phase21-context.jpg', 'ACD24-0180-033', 'Phase 21 context-spectrum context'),
  stereo('phase22-context.jpg', 'NHQ202105050014', 'Phase 22 locked-transfer context')
];

const looksLikeJpeg = (buffer) =>
  buffer.length > 50_000 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff;

async function download(asset) {
  let lastError;
  for (const url of asset.urls) {
    try {
      const response = await fetch(url, {
        redirect: 'follow',
        headers: {
          'user-agent': 'AegisLandResearchCockpit/2.0 (licensed NASA editorial media fetch)'
        }
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const buffer = Buffer.from(await response.arrayBuffer());
      if (!looksLikeJpeg(buffer)) throw new Error(`unexpected payload (${buffer.length} bytes)`);
      const target = path.join(outputDir, asset.file);
      const temporary = `${target}.tmp`;
      await fs.writeFile(temporary, buffer);
      await fs.rename(temporary, target);
      console.log(`✓ ${asset.label}: ${asset.file} (${Math.round(buffer.length / 1024)} KiB)`);
      return;
    } catch (error) {
      lastError = error;
      console.warn(`Media fetch failed for ${asset.file} from ${url}: ${error.message}`);
    }
  }
  throw new Error(`Unable to fetch ${asset.file}: ${lastError?.message || 'unknown error'}`);
}

async function runPool(items, concurrency = 4) {
  let next = 0;
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (next < items.length) {
      const current = items[next++];
      await download(current);
    }
  });
  await Promise.all(workers);
}

await fs.mkdir(outputDir, { recursive: true });
await runPool(assets, 4);
console.log(`✓ Editorial media ready: ${assets.length} local NASA photographs`);
