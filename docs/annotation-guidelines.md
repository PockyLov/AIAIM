# Annotation Guidelines - Phase 2 Dataset Preparation / Annotation Pipeline

## Phase

Phase 2: Dataset Preparation / Annotation Pipeline.

## Class Definition

Only one class is allowed:

```text
0 yellow_ball
```

`yellow_ball` means the yellow spherical AIMLAB target that should be detected in future object-detection training.

## Do Not Annotate

Do not label:

- Yellow UI
- Score text
- Crosshair
- Muzzle flash or weapon effects
- Background highlights
- Non-spherical yellow decorations
- Distant tiny points that cannot be confidently identified as targets

## Bounding Box Rules

- Box the visible yellow-ball body.
- Keep the box close to the visible ball outline.
- Do not include large background regions.
- Do not box a broad glow halo as the target.
- If the edge is slightly blurred, box the visible ball area that a human can identify.
- If the ball is partially occluded but still clearly identifiable, box only the visible part.
- If multiple yellow balls exist in one image, annotate each yellow ball.
- If no yellow ball exists, keep an empty `.txt` label file as a negative sample.

## OpenCV Pre-Labeling Rules

OpenCV is only offline annotation assistance for static screenshots.

- OpenCV label drafts must be manually reviewed.
- Correct detections may be kept.
- Boxes that are too large, too small, on UI, or on visual effects must be corrected.
- Missed yellow balls must be manually added.
- False detections must be removed from the label file.
- Images without yellow balls should keep empty `.txt` labels as negative samples.

OpenCV pre-labels are not final truth until human review is complete.

## Negative Samples

- Images without `yellow_ball` may be kept.
- Their label file must exist and be empty.
- Recommended negative sample ratio: 10%-20% of the final dataset.

## Quality Requirements

- Do not miss clear yellow balls.
- Do not label yellow UI or highlights as targets.
- Do not mix in other classes.
- `class_id` must be `0`.
- Every image must have a same-stem `.txt` label file.
- OpenCV pre-labels must not be used as final training labels without review.

## Recommended Review Tools

- Preferred: LabelImg
- Alternative: Label Studio
- CVAT is not the Phase 2 MVP path.

## LabelImg Workflow

1. Open the selected image directory.
2. Load or correct the OpenCV-generated YOLO labels.
3. Set save format to YOLO.
4. Use only the `yellow_ball` class.
5. Save the `.txt` label file.
6. Ensure every image has a label file.
7. For negative samples, create an empty `.txt` file.
