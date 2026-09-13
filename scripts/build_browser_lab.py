"""Package audited Python methods for the static site's in-browser experiment runner.

No scientific results, frozen candidates, or protected evaluation entrypoints are
included. Later-phase pure functions are copied verbatim from a pinned source.
"""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = '668d065f4312e33e2d21ca7a7ee76d4d6d5617b3'

def build():
    files = {}
    provenance = []
    for path in sorted((ROOT / 'src/uav_safety').glob('*.py')):
        files['uav_safety/' + path.name] = path.read_text(encoding='utf-8')
    selections = {
        'scripts/run_phase14_uncertainty_recoverability_bridge.py': ['_finite_upper_quantile'],
        'scripts/run_phase13_external_validity_gauntlet.py': ['_lagged'],
        'scripts/run_phase20_shapley_context_attenuation.py': ['_all_subsets', '_subset_key', '_shapley_attenuation'],
        'scripts/run_phase21_orthogonal_context_spectrum.py': ['_walsh_spectrum'],
        'scripts/run_phase22_frozen_additive_context_transfer.py': ['_model_from_spectrum', '_predict'],
    }
    chunks = ['from __future__ import annotations\nimport numpy as np\nimport math\nimport itertools\nimport types\nFACTORS = ("edge", "oblique", "dim", "blur_noise", "low_contrast")\n']
    for path, names in selections.items():
        source = subprocess.check_output(['git', 'show', f'{PIN}:{path}'], cwd=ROOT).decode('utf-8')
        tree = ast.parse(source)
        for name in names:
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
            code = ast.get_source_segment(source, node)
            chunks.append(code + '\n')
            provenance.append({'path': path, 'function': name, 'commit': PIN, 'sha256': hashlib.sha256(code.encode()).hexdigest()})
    chunks.append('p20 = types.SimpleNamespace(_all_subsets=_all_subsets, _subset_key=_subset_key)\n')
    source = (ROOT / 'src/uav_safety/trace_validation.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    for name in ('_finite', '_empirical_ks', '_quantile_w1'):
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        chunks.append(ast.get_source_segment(source, node) + '\n')
    files['phase_math.py'] = '\n'.join(chunks)
    files['browser_experiments.py'] = (ROOT / 'scripts/browser_experiments.py').read_text(encoding='utf-8')
    payload = {'schema': 1, 'math_source_commit': PIN, 'core_source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(), 'provenance': provenance, 'files': files}
    target = ROOT / 'deploy/vercel/lab/python-bundle.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding='utf-8')
    print(f'Packaged {len(files)} Python files, {target.stat().st_size:,} bytes.')

if __name__ == '__main__':
    build()
