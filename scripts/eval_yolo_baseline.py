from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 3 offline YOLO baseline validation.")
    parser.add_argument("--weights", type=Path, default=Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt"))
    parser.add_argument("--data", type=Path, default=Path("data/yolo/aimlab_yellow_ball_v1_1/data.yaml"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--project", default=None)
    parser.add_argument("--name", default="phase3_yolo11n_baseline_val")
    parser.add_argument("--out", type=Path, default=Path("runs/detect/phase3_eval_metrics.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.weights.exists():
        raise FileNotFoundError(f"weights not found: {args.weights}")
    if not args.data.exists():
        raise FileNotFoundError(f"data.yaml not found: {args.data}")

    import torch
    from ultralytics import YOLO

    device = args.device if (str(args.device) == "cpu" or torch.cuda.is_available()) else "cpu"
    model = YOLO(str(args.weights))
    val_kwargs = {
        "data": str(args.data),
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": device,
        "workers": args.workers,
        "name": args.name,
    }
    if args.project:
        val_kwargs["project"] = args.project
    metrics = model.val(**val_kwargs)

    row = {
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "mAP50": float(metrics.box.map50),
        "mAP50-95": float(metrics.box.map),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    for key, value in row.items():
        print(f"{key}={value:.6f}")
    print(f"metrics_csv={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
