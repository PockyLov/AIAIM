from __future__ import annotations

import argparse
import sys
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 12.5 YOLO Model Optimization Exporter")
    parser.add_argument("--model", type=Path, required=True, help="Path to raw .pt YOLO model")
    parser.add_argument("--format", choices=["onnx", "engine"], default="onnx", help="Export format (onnx or engine)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size for export")
    parser.add_argument("--half", action="store_true", default=True, help="Export in FP16 half precision")
    parser.add_argument("--dynamic", action="store_true", default=False, help="Dynamic axes")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    
    if not args.model.exists():
        print(f"Error: Model not found at {args.model}", file=sys.stderr)
        return 1
        
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics is not installed. Run: pip install ultralytics", file=sys.stderr)
        return 1
        
    print(f"Loading raw model: {args.model}")
    try:
        model = YOLO(str(args.model))
    except Exception as e:
        print(f"Failed to load model: {e}", file=sys.stderr)
        return 1
        
    print(f"Exporting model to {args.format} format (half={args.half}, imgsz={args.imgsz}, dynamic={args.dynamic})...")
    try:
        exported_path = model.export(
            format=args.format,
            half=args.half,
            imgsz=args.imgsz,
            dynamic=args.dynamic,
            simplify=True if args.format == "onnx" else False
        )
        print(f"Export successful! Optimized model saved to: {exported_path}")
    except Exception as e:
        print(f"Failed to export model: {e}", file=sys.stderr)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
