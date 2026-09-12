from pathlib import Path
import argparse
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]


def build(output, base_path):
    base = '/' + base_path.strip('/') if base_path.strip('/') else ''
    if not re.fullmatch(r'(?:/[A-Za-z0-9_.-]+)*', base):
        raise ValueError('Base path must contain only URL-safe path segments')
    output = output.resolve()
    if output == ROOT or ROOT in output.parents and output.name != '_pages':
        raise ValueError('Use a separate output directory or the repository _pages folder')
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'deploy/vercel', output, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('vercel.json', 'fetch-editorial-media.mjs'))
    shutil.copytree(ROOT / 'dashboard', output / 'dashboard', dirs_exist_ok=True)
    config = json.loads((ROOT / 'deploy/vercel/vercel.json').read_text())
    routes = {rule['source'].rstrip('/'): rule['destination'] for rule in config['rewrites']}
    for rule in config['rewrites']:
        source, destination = rule['source'], rule['destination']
        if ':' in source or source == '/favicon.ico':
            continue
        target = output / source.strip('/')
        if '.' not in target.name:
            target = target / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output / destination.lstrip('/'), target)
    taxonomy = (ROOT / 'dashboard/phase-taxonomy.js').read_text()
    slugs = re.findall(r'^    (phase\d+[a-z]*): \{ category:', taxonomy, re.M)
    assert len(slugs) == 26, 'Unexpected phase count; review the route list'
    for slug in slugs:
        target = output / 'phases' / slug / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        source = routes.get('/phases/' + slug, '/dashboard/phases/phase.html')
        shutil.copyfile(output / source.lstrip('/'), target)
    origin = 'https://suhaslord.github.io' + base
    for file in output.rglob('*'):
        if file.suffix not in {'.html', '.css', '.js'}:
            continue
        text = file.read_text()
        text = text.replace('https://aegisland-research-cockpit.vercel.app', origin)
        if base:
            text = re.sub(r'''(["'`])/(?!/)(?=[A-Za-z0-9?#]|["'`])''',
                          lambda match: match[1] + base + '/', text)
            text = re.sub(r'url\(/(?!/)', 'url(' + base + '/', text)
        file.write_text(text)
    (output / '.nojekyll').touch()
    (output / '404.html').write_text(f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page not found · AegisLand</title><link rel="stylesheet" href="{base}/aegisland.css">
<main class="wrap"><h1>That page isn’t here.</h1><p>You can find all published research in the archive.</p>
<a class="button primary" href="{base}/phases/">Browse the research</a></main></html>''')
    required = ['presentation.css', 'presentation.js', 'film/aerocast-flight.mp4',
                'film/aerocast-poster.jpg', 'frozen-lineage.js']
    required += ['phases/' + slug + '/index.html' for slug in slugs]
    for name in required:
        if not (output / name).is_file():
            raise RuntimeError('Missing release file: ' + name)
    print(f'Built {len(slugs)} phase routes at {origin}/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / '_pages')
    parser.add_argument('--base-path', default='/uav-safety-research')
    args = parser.parse_args()
    build(args.output, args.base_path)
