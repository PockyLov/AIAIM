from __future__ import annotations

import argparse
import csv
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 3 offline prediction review for val/test images.")
    parser.add_argument("--weights", type=Path, default=Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt"))
    parser.add_argument("--dataset", type=Path, default=Path("data/yolo/aimlab_yellow_ball_v1_1"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0")
    parser.add_argument("--conf", nargs="+", type=float, default=[0.25, 0.50])
    parser.add_argument("--out", type=Path, default=Path("runs/detect/phase3_prediction_review_summary.csv"))
    return parser.parse_args()


def list_images(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> int:
    args = parse_args()
    if not args.weights.exists():
        raise FileNotFoundError(f"weights not found: {args.weights}")

    import torch
    from ultralytics import YOLO

    device = args.device if (str(args.device) == "cpu" or torch.cuda.is_available()) else "cpu"
    model = YOLO(str(args.weights))
    rows: list[dict[str, object]] = []

    for split in ("val", "test"):
        image_dir = args.dataset / "images" / split
        images = list_images(image_dir)
        for conf in args.conf:
            conf_tag = f"{int(conf * 100):03d}"
            run_name = f"phase3_predict_{split}_conf{conf_tag}"
            results = model.predict(
                source=str(image_dir),
                imgsz=args.imgsz,
                conf=conf,
                device=device,
                name=run_name,
                save=True,
                exist_ok=True,
                verbose=False,
            )
            by_name = {Path(result.path).name: len(result.boxes) for result in results}
            output_dir = Path("runs/detect") / run_name
            for image_path in images:
                rows.append(
                    {
                        "split": split,
                        "image_name": image_path.name,
                        "image_path": str(image_path),
                        "conf": f"{conf:.2f}",
                        "prediction_count": by_name.get(image_path.name, 0),
                        "review_output_path": str(output_dir / image_path.name),
                    }
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["split", "image_name", "image_path", "conf", "prediction_count", "review_output_path"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"review_summary={args.out}")
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
