from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 3 YOLO11n baseline training.")
    parser.add_argument("--data", type=Path, default=Path("data/yolo/aimlab_yellow_ball_v1_1/data.yaml"))
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--project", default=None)
    parser.add_argument("--name", default="phase3_yolo11n_baseline")
    parser.add_argument("--exist-ok", action="store_true")
    return parser.parse_args()


def environment_summary() -> dict[str, object]:
    import torch
    import ultralytics

    cuda_available = torch.cuda.is_available()
    return {
        "python": platform.python_version(),
        "ultralytics": ultralytics.__version__,
        "torch": torch.__version__,
        "cuda_available": cuda_available,
        "gpu_name": torch.cuda.get_device_name(0) if cuda_available else None,
    }


def main() -> int:
    args = parse_args()
    if not args.data.exists():
        raise FileNotFoundError(f"data.yaml not found: {args.data}")

    from ultralytics import YOLO

    env = environment_summary()
    device = args.device
    if str(args.device) != "cpu" and not env["cuda_available"]:
        print("cuda_available=false fallback_device=cpu")
        device = "cpu"

    print("Run dataset validation first if not already done:")
    print(f"  python scripts/validate_yolo_dataset.py --dataset {args.data.parent}")
    print("environment=" + json.dumps(env, ensure_ascii=False))

    train_kwargs = {
        "data": str(args.data),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": device,
        "workers": args.workers,
        "patience": args.patience,
        "seed": args.seed,
        "name": args.name,
        "exist_ok": args.exist_ok,
    }
    if args.project:
        train_kwargs["project"] = args.project

    model = YOLO(args.model)
    results = model.train(**train_kwargs)

    run_dir = Path("runs") / "detect" / args.name if args.project is None else Path(args.project) / args.name
    expected = [
        run_dir / "weights" / "best.pt",
        run_dir / "weights" / "last.pt",
        run_dir / "results.csv",
    ]
    for path in expected:
        print(f"exists:{path}={path.exists()}")
    print(f"run_dir={run_dir}")
    if hasattr(results, "results_dict"):
        print("metrics=" + json.dumps(results.results_dict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
