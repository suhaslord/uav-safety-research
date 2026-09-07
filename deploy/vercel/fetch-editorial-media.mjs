import fs from 'node:fs/promises';
import path from 'node:path';

const outputDir = path.resolve(process.env.AEGIS_EDITORIAL_MEDIA_DIR || 'deploy/vercel/media');

const assets = [
  {
    file: 'acero-uav-flight.jpg',
    label: 'NASA Ames ACERO UAV flight reference',
    urls: [
      'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Advanced_Capabilities_for_Emergency_Response_Operations_%28ACERO%29_%28ACD24-0180-035%29.jpg/1280px-Advanced_Capabilities_for_Emergency_Response_Operations_%28ACERO%29_%28ACD24-0180-035%29.jpg',
      'https://upload.wikimedia.org/wikipedia/commons/7/7a/Advanced_Capabilities_for_Emergency_Response_Operations_%28ACERO%29_%28ACD24-0180-035%29.jpg'
    ]
  },
  {
    file: 'acero-uav-landing.jpg',
    label: 'NASA Ames ACERO landing reference',
    urls: [
      'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Advanced_Capabilities_for_Emergency_Response_Operations_%28ACERO%29_%28ACD24-0180-037%29.jpg/1280px-Advanced_Capabilities_for_Emergency_Response_Operations_%28ACERO%29_%28ACD24-0180-037%29.jpg',
      'https://upload.wikimedia.org/wikipedia/commons/8/8c/Advanced_Capabilities_for_Emergency_Response_Operations_%28ACERO%29_%28ACD24-0180-037%29.jpg'
    ]
  }
];

const looksLikeJpeg = (buffer) => buffer.length > 50_000 && buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff;

async function download(asset) {
  let lastError;
  for (const url of asset.urls) {
    try {
      const response = await fetch(url, {
        redirect: 'follow',
        headers: {
          'user-agent': 'AegisLandResearchCockpit/1.0 (editorial media fetch; public-domain NASA imagery)'
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

await fs.mkdir(outputDir, { recursive: true });
for (const asset of assets) await download(asset);
