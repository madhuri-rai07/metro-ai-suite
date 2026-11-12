# Pipeline Defect Detection — Agentic Predictive Maintenance

This directory contains the use-case-specific configuration for the
**Pipeline Defect Detection** sample application, built on the
Agentic Predictive Maintenance Blueprint from `metro-ai-suite`.

> **Demonstration only:** The Geti-trained YOLOX-L model is not validated for
> operational, engineering, safety, or asset-integrity decisions. Predictions
> require qualified human review; no automatic equipment control is intended.

## Quick Start

After the [HF model PR](https://huggingface.co/open-edge-platform/apm-pipeline-defect-detection/discussions/1)
is merged, download the reviewed model and notices before launching APM:

```bash
cd <metro-ai-suite>/agentic-predictive-maintenance-pipeline
python3.12 apps/pipeline-defect-detection/download_model.py
# Prepare resources/videos/datastream.mp4 as described in the getting-started guide.
LLM_MODE=fallback source ./setup.sh --use-case pipeline-defect-detection
```

For LLM reasoning, prepare the LLM separately following the
[getting-started guide](../../docs/user-guide/get-started.md), then start without
the fallback override. Fallback mode skips the LLM, not video inference.

The standard-library downloader fetches seven files from
[`open-edge-platform/apm-pipeline-defect-detection`](https://huggingface.co/open-edge-platform/apm-pipeline-defect-detection)
at immutable revision `86a3169310e91fcdaea0aab45f1ade616fced081`. This pins the reviewed
artifact commit, not a moving `main` or PR ref. If review changes the artifacts,
update the revision and checksums in `download_model.py` and all pipeline paths
together before merging this integration.

Downloads are size- and SHA-256-checked and installed atomically under
`models/hf/<revision>/`. Existing legacy XML/BIN files are not used or overwritten.
A valid cache is reused offline; an incomplete or modified cache fails rather
than silently deploying another model. The downloaded model card, Apache-2.0
license, and dataset attribution remain beside the model. The weights and dataset
are not added to this source repository.

## Directory Structure

```
apps/pipeline-defect-detection/
├── configs/
│   ├── agents.yaml                    # Agent pipeline configuration
│   ├── pipeline-server-config.json    # DL Streamer pipeline definition
│   └── policy_fallback.json           # Rule-based fallback thresholds
├── models/
│   ├── pipeline-defect-detection.json # DL Streamer preprocessing and class mapping
│   └── hf/<revision>/                # Downloaded model and notices (gitignored)
├── download_model.py                 # Pinned, checksum-verified download
├── prompts/
│   └── pipeline-defect-detection.txt  # LLM prompts (section-based)
└── .env_pipeline-defect-detection     # Environment variable overrides
```

## Model Classes and Review Policy

| Output ID | Exact label | Interpretation |
|---|---|---|
| 0 | gas-pipelines | Pipeline context, not proof of damage or normal operation |
| 1 | deformation | Candidate deformation requiring human review |
| 2 | corrosion | Candidate corrosion requiring human review |
| 3 | coating degradation | Candidate coating degradation; low reported model score |
| 4 | deformations | Separate model class; positive behavior remains unverified |

Preserve both deformation labels and their IDs. Inference uses confidence `0.25`;
illustrative agent review thresholds use average confidence `0.7` for every class.
These are not calibrated defect-severity thresholds. All fallback actions are
`MONITOR`; there are no critical classes or shutdown commands. The external
fallback agent can mark any threshold crossing, including pipeline context, as a
violation and assign a HIGH ticket priority. That is a demonstration review flag,
not an asset-risk assessment. The LLM prompts explicitly require human review
and prohibit integrity, compliance, and safety claims.

## DL Streamer Preprocessing

The model has FP16-compressed weights and FP32 NCHW input `[1, 3, 640, 640]`.
CPU/GPU/NPU pipeline definitions select the same pinned XML and local model-proc,
with BGR video frames, OpenCV preprocessing, RGB conversion, centered aspect-ratio
letterboxing, padding `114.0`, and no division by 255. The local model-proc adds
this input contract to the HF file's `boxes_labels` output mapping; the downloaded
HF model-proc alone does not configure deployment preprocessing.

The IR already performs class-aware non-maximum suppression (NMS). The adapter
sets `iou_threshold: 1.0` to prevent the older `boxes_labels` converter's extra,
class-agnostic NMS from discarding overlapping pipeline and defect detections.
It also sets `nms_execute: false` for newer converters that support that flag.
The model's embedded NMS remains unchanged.

CPU inference must be validated on the deployed DL Streamer image. GPU/NPU entries
are retained but require compatible hardware and separate device validation;
their presence is not a compatibility guarantee.

## Adapting to a New Use Case

To create a new use case (e.g., weld defect detection):

1. Copy this directory: `cp -r pipeline-defect-detection weld-defect-detection`
2. Update `configs/agents.yaml` — change `use_case_id` and defect classes
3. Update `configs/pipeline-server-config.json` — point to new model
4. Update `configs/policy_fallback.json` — set per-class thresholds
5. Update `prompts/weld-defect-detection.txt` — domain-specific prompts
6. Supply the new XML/BIN and matching model-proc; replace the pinned downloader
   rather than pointing a new use case at this model's revision
7. Run: `./setup.sh --use-case weld-defect-detection`

No code changes required.
