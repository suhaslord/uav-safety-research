"""Exercise actual packaged-home assertions before a production-only failure."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', [
    'Assert frozen Tesla-style release is native and self-contained',
    'Verify deployed frozen archive and public alias',
])
def test_production_home_assertions_match_current_presentation(name):
    workflow = (ROOT / '.github/workflows/emergency-vercel-deploy.yml').read_text(encoding='utf-8')
    # This is one known workflow block, not a general YAML parser. Keep the test
    # standard-library-only, like the project's declared development environment.
    marker = f'      - name: {name}\n'
    assert workflow.count(marker) == 1
    block = workflow.split(marker, 1)[1].split('\n      - ', 1)[0]
    commands = [line.strip().replace('.vercel-release/index.html', 'deploy/vercel/index.html')
                for line in block.splitlines()
                if 'grep' in line and any(target in line for target in
                    ['.vercel-release/index.html', '$PUBLIC_HTML', '$HOME_HTML'])]
    minimum = 30 if name.startswith('Assert') else 25
    assert len(commands) >= minimum, 'Do not silently stop exercising the evidence and boundary gates'
    # Binary stdin preserves LF for Git Bash on Windows; text mode inserts CRLF.
    setup = 'set -euo pipefail\nPUBLIC_HTML="$(< deploy/vercel/index.html)"\nHOME_HTML="$PUBLIC_HTML"\n'
    script = (setup+'\n'.join(commands)+'\n').encode('utf-8')
    result = subprocess.run(['bash', '-s'], input=script,
                            cwd=ROOT, capture_output=True,
                            env={**os.environ, 'LANG': 'C.UTF-8'})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')


def test_home_uses_one_deliberate_stylesheet_stack():
    home = (ROOT / 'deploy/vercel/index.html').read_text(encoding='utf-8')
    assert 'href="/home-evidence.css?v=' in home
    for legacy in ['research-home.css', 'research-media.css', 'ui-review.css', 'site-refresh.css', 'tesla-bundle.css']:
        assert f'href="/{legacy}' not in home
