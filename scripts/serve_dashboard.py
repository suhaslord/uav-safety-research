from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the AegisLand research cockpit locally.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    dashboard_dir = repo_root / "dashboard"
    if not dashboard_dir.exists():
        raise FileNotFoundError(f"Dashboard directory not found: {dashboard_dir}")

    os.chdir(dashboard_dir)
    server = ThreadingHTTPServer((args.host, args.port), SimpleHTTPRequestHandler)
    print(f"AegisLand Research Cockpit: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the local server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
