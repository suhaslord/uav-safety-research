"""Exercise actual packaged-home assertions before a production-only failure."""
from pathlib import Path
import os
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_production_home_assertions_match_current_presentation():
    workflow = yaml.safe_load((ROOT / '.github/workflows/emergency-vercel-deploy.yml').read_text(encoding='utf-8'))
    step = next(s for s in workflow['jobs']['deploy']['steps']
                if s.get('name') == 'Assert frozen Tesla-style release is native and self-contained')
    commands = [line.strip().replace('.vercel-release/index.html', 'deploy/vercel/index.html')
                for line in step['run'].splitlines()
                if 'grep' in line and '.vercel-release/index.html' in line]
    assert len(commands) >= 30, 'Do not silently stop exercising the evidence and boundary gates'
    # Binary stdin preserves LF for Git Bash on Windows; text mode inserts CRLF.
    script = ('set -euo pipefail\n'+'\n'.join(commands)+'\n').encode('utf-8')
    result = subprocess.run(['bash', '-s'], input=script,
                            cwd=ROOT, capture_output=True,
                            env={**os.environ, 'LANG': 'C.UTF-8'})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')


def test_home_uses_one_deliberate_stylesheet_stack():
    home = (ROOT / 'deploy/vercel/index.html').read_text(encoding='utf-8')
    assert 'href="/home-evidence.css?v=' in home
    for legacy in ['research-home.css', 'research-media.css', 'ui-review.css', 'site-refresh.css', 'tesla-bundle.css']:
        assert f'href="/{legacy}' not in home
