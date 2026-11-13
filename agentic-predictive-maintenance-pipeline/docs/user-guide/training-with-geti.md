# Training a Defect Detection Model with Intel Geti

The reference use case downloads a Geti-trained YOLOX-L OpenVINO model from
[`open-edge-platform/apm-pipeline-defect-detection`](https://huggingface.co/open-edge-platform/apm-pipeline-defect-detection).
It is demonstration-only, not validated for production, safety, or asset-integrity
decisions. See the [use-case README](../../apps/pipeline-defect-detection/README.md)
for the pinned download command, preprocessing, and known limitations.

Use Intel Geti to train and export a deployment-ready detector when you have a production dataset
for your inspection scenario.

## Training Workflow

1. Collect representative images or video frames from the target environment. Include normal
   examples and each defect class that the application must detect. For the `pipeline-defect-detection`
   use case, you can use the public
   [Gas Pipelines Dataset on Kaggle](https://www.kaggle.com/datasets/sardaanaeginova/gas-pipelines)
   as a starting point, subject to its attribution and license terms. Validate
   representative production data independently before operational use.
2. Create a Geti object detection project.
3. Define the defect labels. For the reference pipeline use case, the application configuration
   expects these labels:

   ```text
   gas-pipelines
   deformation
   corrosion
   coating degradation
   deformations
   ```

   These are the exact model-output labels in ID order, not a severity taxonomy.
   Preserve the distinct `deformation` and `deformations` IDs; `gas-pipelines`
   alone establishes neither damage nor safe operation.
   If you use different labels, update the APM configuration files listed in
   [Update APM Configuration](#update-apm-configuration).
4. Upload the dataset and annotate bounding boxes for each defect instance.
5. Train the model in Geti and review validation metrics. Do not proceed to deployment until the
   dataset covers expected camera angles, lighting, backgrounds, defect sizes, and negative samples.
6. Export the trained model in OpenVINO Intermediate Representation (IR) format. The exported model
   should include `.xml` and `.bin` artifacts.

## Install the Exported Model

Place the exported OpenVINO model artifacts in the use-case model directory. The default
`pipeline-server-config.json` expects the detector at this path inside the DL Streamer Pipeline
Server container:

```text
/home/pipeline-server/models/hf/86a3169310e91fcdaea0aab45f1ade616fced081/model.xml
```

That container path maps to the host directory selected by `USE_CASE_MODELS_DIR`, which is normally:

```text
apps/pipeline-defect-detection/models/
```

For a new custom export, use a separate directory; do not overwrite the
checksum-verified HF cache. For example:

```text
apps/pipeline-defect-detection/models/custom/model.xml
apps/pipeline-defect-detection/models/custom/model.bin
```

If you use a different model filename, update every CPU/GPU/NPU pipeline entry in:

```text
apps/pipeline-defect-detection/configs/pipeline-server-config.json
```

For example:

```json
"pipeline": "{auto_source} name=source ! decodebin3 ! videoconvert ! video/x-raw,format=BGR ! gvadetect model=/home/pipeline-server/models/custom/model.xml model-proc=/home/pipeline-server/models/pipeline-defect-detection.json pre-process-backend=opencv device=CPU threshold=0.25 name=detection ! gvametaconvert add-empty-results=true name=metaconvert ! queue ! gvafpscounter ! appsink name=destination"
```

Update every device-specific pipeline and the model-proc to match the new export.
The example assumes the same FP32 NCHW/RGB/centered-letterbox contract as the
reference export. Do not reuse that preprocessing for a different input contract,
such as an export with embedded U8/NHWC preprocessing.

## Update APM Configuration

The detector labels must stay aligned with the reasoning and fallback configuration:

| File | What to update |
|------|----------------|
| `apps/pipeline-defect-detection/configs/agents.yaml` | `policy.defect_classes`, critical classes, and severity mapping |
| `apps/pipeline-defect-detection/configs/policy_fallback.json` | Per-class confidence thresholds and fallback actions |
| `apps/pipeline-defect-detection/prompts/pipeline-defect-detection.txt` | Defect class descriptions and reasoning instructions |
| `apps/pipeline-defect-detection/configs/pipeline-server-config.json` | Model path and detection threshold |
| `apps/pipeline-defect-detection/models/pipeline-defect-detection.json` | Input preprocessing and exact output-label mapping |

If you create a new use case, copy the full use-case directory and update the file names and
`use_case_id` consistently:

```bash
cp -r apps/pipeline-defect-detection apps/<new-use-case>
```

## Validate the Trained Model

After installing the exported model:

1. Start the application:

   ```bash
   source ./setup.sh --use-case pipeline-defect-detection
   ```

2. Open the dashboard and run an inspection on a validation video.
3. Confirm detections are stored:

   ```bash
   curl http://localhost:8080/api/storage/detections/summary
   ```

4. Review DL Streamer logs if detections are missing:

   ```bash
   docker logs apm-dlstreamer
   docker logs apm-detection
   ```

5. Tune the `gvadetect threshold=` value in `pipeline-server-config.json` and the policy thresholds
   in `policy_fallback.json` based on validation results.

## Dataset Readiness Guidance

Before treating a model as release-ready, verify that the dataset includes:

- Representative production camera views and image quality.
- Enough examples for each defect class and enough negative or no-defect examples.
- Variation in lighting, backgrounds, object scale, occlusion, and motion blur.
- A separate validation set that was not used for training.
- Clear label definitions so annotators apply bounding boxes consistently.

Do not use the reference model as evidence of production defect detection accuracy. It is provided
only to demonstrate the APM application flow.
