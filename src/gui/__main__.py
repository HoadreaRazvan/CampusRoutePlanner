"""Starts the web GUI:  python -m src.gui [graph_folder] [--port 8765] [--no-browser]"""
import argparse
import sys
import webbrowser
from urllib.parse import quote

from src.gui.server import create_server
from src.io import InputValidationError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.gui", description="Campus Route Planner web interface.")
    parser.add_argument("graph", nargs="?", help="optional graph folder to open first (e.g. an unseen graph)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser automatically")
    args = parser.parse_args(argv)

    server = create_server(args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if args.graph:
        try:
            url += f"#{quote(server.registry.add_folder(args.graph))}"
        except InputValidationError as err:
            print(f"error: {err}", file=sys.stderr)
            server.server_close()
            return 2

    print(f"Campus Route Planner GUI running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
