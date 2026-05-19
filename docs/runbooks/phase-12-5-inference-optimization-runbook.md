# Phase 12.5 Runbook: Inference Engine Optimization

## Overview
Phase 12.5 focuses on overcoming the YOLO PyTorch overhead by introducing dynamic execution of hardware-optimized model binaries such as ONNX (`.onnx`) or TensorRT (`.engine`). This transition aims to drop inference latency below the critical 200ms threshold.

## Exporting an Optimized Model

A new dedicated script is provided to convert PyTorch `.pt` files to an optimized structure:

```powershell
.\.venv\Scripts\python.exe scripts\export_optimized_model.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --format onnx `
  --half
```

### Options:
- `--format`: `onnx` or `engine` (default is `onnx`). `engine` requires TensorRT bindings installed.
- `--half`: Generates FP16 weights which execute significantly faster on modern GPUs.
- `--imgsz`: Locks the static execution size for the inference plane (default `640`).

## Dynamic Engine Loading Fallback

You **do not** need to change the standard `--model` argument when running the main scripts (`live_finite_repeat_aim_click.py`, `live_one_shot_fov_aim.py`, etc.). 
The system uses the following priority fallback:
1. `best.engine` (If TensorRT is present and exported)
2. `best.onnx` (If ONNX Runtime is exported)
3. `best.pt` (Fallback to standard slow PyTorch)

When a script launches, the CLI will output: `Phase 12.5: Found optimized ONNX model: ...` if the acceleration layer was successfully applied.

## Dependencies

Ensure your environment possesses the hardware accelerators via:
```powershell
python -m pip install onnx>=1.15.0 onnxruntime-gpu>=1.17.0
```
