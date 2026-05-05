from __future__ import annotations

import argparse
from pathlib import Path

from .collector_service import CollectorService, CollectorSettings
from .hotkey_controller import HotkeyController
from .logging_setup import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="aiaim-collect-screenshots",
        description="AIAIM Phase 1 foreground-gated AIMLAB screenshot collector.",
    )
    parser.add_argument(
        "--mode",
        choices=("single", "hotkeys"),
        default="single",
        help="Capture one screenshot attempt or run the F8/F9/Esc hotkey controller.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="AIAIM project root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Screenshot and metadata directory. Defaults to data/raw/screenshots/.",
    )
    parser.add_argument(
        "--title-keyword",
        action="append",
        default=None,
        help="AIMLAB window title keyword. Can be passed multiple times.",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=500,
        help="Continuous screenshot interval for hotkey mode.",
    )
    parser.add_argument(
        "--coverage-warning-threshold",
        type=float,
        default=0.95,
        help="Warn when AIMLAB window covers less than this ratio of its monitor.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    logger = configure_logging(project_root / "logs")
    settings = CollectorSettings(
        project_root=project_root,
        title_keywords=tuple(args.title_keyword or ("aimlab", "aim lab")),
        output_dir=args.output_dir.resolve() if args.output_dir else None,
        fullscreen_warning_threshold=args.coverage_warning_threshold,
    )
    service = CollectorService(settings=settings, logger=logger)

    if args.mode == "single":
        metadata = service.capture_once("single")
        print(f"blocked={metadata['blocked']} reason={metadata['blocked_reason']}")
        print(f"image_path={metadata['image_path']}")
        print(f"metadata_path={metadata['metadata_path']}")
        return 2 if metadata["blocked"] else 0

    controller = HotkeyController(service=service, interval_ms=args.interval_ms, logger=logger)
    controller.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
