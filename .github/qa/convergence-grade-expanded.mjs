import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import sharp from 'sharp';

const BASE = process.env.QA_BASE_URL;
if (!BASE) throw new Error('QA_BASE_URL is required');

const SOURCE = '.github/qa/convergence-grade.mjs';
const GENERATED = '.github/qa/.convergence-grade-secondary.generated.mjs';
const PRIMARY_ROOT = path.join('qa-artifacts', 'convergence-grade');
const SECONDARY_ROOT = path.join('qa-artifacts', 'convergence-grade-secondary');
const FINAL_ROOT = path.join('qa-artifacts', 'convergence-grade-560');

const run = (script) => new Promise((resolve) => {
  const child = spawn(process.execPath, [script], {
    stdio: 'inherit',
    env: { ...process.env, QA_BASE_URL: BASE }
  });
  child.on('exit', (code) => resolve(code ?? 1));
});

const source = await fs.readFile(SOURCE, 'utf8');
const secondaryViewports = `const viewports = [
  { name:'laptop', width:1280, height:800 },
  { name:'tablet', width:768, height:1024, hasTouch:true }
];`;

let secondary = source
  .replace("const ROOT = path.join('qa-artifacts', 'convergence-grade');", "const ROOT = path.join('qa-artifacts', 'convergence-grade-secondary');")
  .replace(/const viewports = \[[\s\S]*?\n\];/, secondaryViewports)
  .replace(
    /if \(\(counts\.desktop\|\|0\) !== 140\) block\('global','desktop-screenshot-count',\{count:counts\.desktop\|\|0\}\);\nif \(\(counts\.phone\|\|0\) !== 140\) block\('global','phone-screenshot-count',\{count:counts\.phone\|\|0\}\);/,
    "if ((counts.laptop||0) !== 140) block('global','laptop-screenshot-count',{count:counts.laptop||0});\nif ((counts.tablet||0) !== 140) block('global','tablet-screenshot-count',{count:counts.tablet||0});"
  )
  .replace('`- Desktop screenshots: ${counts.desktop||0}`', '`- Laptop screenshots: ${counts.laptop||0}`')
  .replace('`- Phone screenshots: ${counts.phone||0}`', '`- Tablet screenshots: ${counts.tablet||0}`');

if (secondary === source || !secondary.includes("name:'laptop'") || !secondary.includes('convergence-grade-secondary')) {
  throw new Error('Failed to generate secondary convergence scan');
}

await fs.writeFile(GENERATED, secondary);
await fs.rm(FINAL_ROOT, { recursive: true, force: true });
await fs.mkdir(FINAL_ROOT, { recursive: true });

const primaryCode = await run(SOURCE);
const secondaryCode = await run(GENERATED);
await fs.rm(GENERATED, { force: true });

const walkPngs = async (dir) => {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const out = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...await walkPngs(full));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith('.png')) out.push(full);
  }
  return out;
};

const primaryShots = await walkPngs(path.join(PRIMARY_ROOT, 'screenshots')).catch(() => []);
const secondaryShots = await walkPngs(path.join(SECONDARY_ROOT, 'screenshots')).catch(() => []);
const shots = [...primaryShots, ...secondaryShots].sort();
const imageAnalyses = [];
const imageBlockers = [];

for (const file of shots) {
  const stat = await fs.stat(file);
  const image = sharp(file, { failOn: 'error' });
  const [metadata, stats] = await Promise.all([image.metadata(), image.stats()]);
  const channelStdev = stats.channels.map((channel) => Number(channel.stdev.toFixed(3)));
  const maxStdev = Math.max(...channelStdev);
  const entropy = Number((stats.entropy ?? 0).toFixed(4));
  const suspiciouslyFlat = entropy < 0.02 && maxStdev < 0.5;
  const suspiciouslyTiny = stat.size < 3500;
  const analysis = {
    file,
    bytes: stat.size,
    width: metadata.width || 0,
    height: metadata.height || 0,
    entropy,
    channelStdev,
    suspiciouslyFlat,
    suspiciouslyTiny
  };
  imageAnalyses.push(analysis);
  if (suspiciouslyFlat || suspiciouslyTiny || !analysis.width || !analysis.height) imageBlockers.push(analysis);
}

const readJson = async (file) => JSON.parse(await fs.readFile(file, 'utf8'));
const primaryReport = await readJson(path.join(PRIMARY_ROOT, 'report.json')).catch(() => null);
const secondaryReport = await readJson(path.join(SECONDARY_ROOT, 'report.json')).catch(() => null);

const expected = 560;
const screenshotCountOk = shots.length >= expected;
const oneAnalysisPerScreenshot = imageAnalyses.length === shots.length;
const combinedBlockers = [
  ...(primaryReport?.blockers || []),
  ...(secondaryReport?.blockers || []),
  ...imageBlockers.map((item) => ({ key: item.file, kind: 'image-level-render-anomaly' }))
];
const combinedWarnings = [
  ...(primaryReport?.warnings || []),
  ...(secondaryReport?.warnings || [])
];

if (!screenshotCountOk) combinedBlockers.push({ key: 'global', kind: 'screenshot-count-below-560', count: shots.length });
if (!oneAnalysisPerScreenshot) combinedBlockers.push({ key: 'global', kind: 'missing-image-analysis', screenshots: shots.length, analyses: imageAnalyses.length });
if (primaryCode !== 0) combinedBlockers.push({ key: 'primary-scan', kind: 'primary-grade-failed', exitCode: primaryCode });
if (secondaryCode !== 0) combinedBlockers.push({ key: 'secondary-scan', kind: 'secondary-grade-failed', exitCode: secondaryCode });

const report = {
  base: BASE,
  screenshotCount: shots.length,
  expectedMinimum: expected,
  screenshotCountOk,
  oneAnalysisPerScreenshot,
  viewportGroups: {
    primary: primaryReport?.counts || {},
    secondary: secondaryReport?.counts || {}
  },
  blockers: combinedBlockers,
  warnings: combinedWarnings,
  imageAnalyses
};

await fs.writeFile(path.join(FINAL_ROOT, 'report.json'), JSON.stringify(report, null, 2));
const summary = [
  '# AegisLand 560-screenshot final UI scan',
  '',
  `- Base: ${BASE}`,
  `- Screenshots captured: ${shots.length}`,
  `- Screenshots image-analyzed: ${imageAnalyses.length}`,
  `- One analysis per screenshot: ${oneAnalysisPerScreenshot ? 'yes' : 'no'}`,
  `- DOM/layout blockers: ${(primaryReport?.blockers?.length || 0) + (secondaryReport?.blockers?.length || 0)}`,
  `- DOM/layout warnings: ${combinedWarnings.length}`,
  `- Image-render anomalies: ${imageBlockers.length}`,
  `- Final blockers: ${combinedBlockers.length}`,
  '',
  '## Final blockers',
  ...(combinedBlockers.length ? combinedBlockers.map((item) => `- ${item.key} — ${item.kind}`) : ['- None'])
].join('\n');
await fs.writeFile(path.join(FINAL_ROOT, 'summary.md'), summary);
console.log(summary);

if (combinedBlockers.length || combinedWarnings.length) process.exit(1);
