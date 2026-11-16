# Reference and Troubleshooting

Configuration reference, internals, limitations and troubleshooting for the Nx Witness
integration.

## Configuration reference

`setup.sh` generates `config/config.yaml` from `config/base.yaml` and the fragments of the
selected VMS and apps. For this integration, the Nx Witness instance is in
`vms_shim/nxwitness/vap-config.yaml`, Loitering Detection in
`analytics_app_shim/object_detection/vap-config.yaml`, and Live Video Captioning in
`analytics_app_shim/lvc/vap-config.yaml`. Edit the fragments, not `config/config.yaml`, and
run `./setup.sh --vms nx --apps <apps>` again.

### Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `NX_HOST` | — | Nx Witness Server address. |
| `NX_USERNAME`, `NX_PASSWORD` | — | Administrator account VAP signs in with. Also used in the RTSP URLs given to the pipelines. |
| `NX_TLS_VERIFY` | `false` | Verify the Nx Witness Server's TLS certificate. |
| `NX_CA_BUNDLE` | empty | CA certificate path inside the backend container, when `NX_TLS_VERIFY=true`. See [TLS and Certificate Configuration](../../tls-and-certificates.md). |
| `UI_HTTPS_PORT` | `3443` | VAP dashboard port. |

The Loitering Detection and LVC variables are described in
[Run Loitering Detection](./run-loitering-detection.md#22-configure-the-environment) and
[Run Live Video Captioning](./run-live-video-captioning.md#22-configure-the-environment).

### Nx Witness instance

| Key | Default | Description |
| --- | --- | --- |
| `name` | `nx-main` | Instance name. Must start with `nx`: pipeline results are routed by the `nx:` prefix of the camera ID. |
| `base_url` | `https://${NX_HOST}:7001` | Nx Witness REST API. |
| `tls_verify`, `tls_ca_bundle` | `false`, empty | TLS verification of the REST API. |
| `auth.username`, `auth.password` | from `.env` | Administrator account. |
| `auth.auth_type` | `digest` | Authentication type. |
| `analytics_manifest_path` | bundled | Integration manifest. Defaults to `vms_shim/nxwitness/nx_integration.json`. |

`vendor_options` of the Nx Witness instance:

| Key | Default | Description |
| --- | --- | --- |
| `type_map` | — | Category → Nx object type, overriding the default `vap.<category>`. For example `{pedestrian: vap.person}`. |
| `zone_type_id` | `vap.zone` | Nx object type of the drawn loitering zone. |
| `metadata_min_duration_ms` | `100` | Minimum time the Desktop Client keeps drawing a box. |
| `metadata_latency_margin_ms` | `500` | Added to the measured detection latency to decide how long a box is drawn. |
| `metadata_max_duration_ms` | `10000` | Maximum time the Desktop Client keeps drawing a box. |

### Loitering Detection app settings

These keys of the `object_detection` app matter for Nx Witness:

| Key | Description |
| --- | --- |
| `display_name` | Name of the app's group in the camera settings. |
| `pipeline.cpu/gpu/npu` | Pipeline for each device. At least one is required. The **Device** field lists the devices set here. |
| `label_map` | Detector label → category. Nx Witness shows the category as `vap.<category>`; unmapped labels as `python.detected.object`. `label_type_map` is deprecated. |
| `zones` | Boxes drawn on the video as `vap.zone`, with a `label` and a normalized `bounding_box`. |
| `default_zone_polygon` | Default value of the **Loitering Zone** field, as normalized `[x, y]` points. |
| `zone_filter_enabled` | Push only the objects the pipeline reports in a zone. Off by default, so every detection is drawn. |
| `loitering_threshold_s` | Threshold sent to the pipeline (on-video text color). |
| `events_enabled` | Add a bookmark for each loitering row. `event_bookmark_enabled` is a deprecated alias. |
| `event_topic_suffix` | MQTT topic suffix of the loitering rows. Must match the recipe's `DEST_TOPIC_SUFFIX`. |
| `metadata_topic_prefix` | MQTT topic prefix. Must match the recipe's `SOURCE_TOPIC_PREFIX`. |

### Live Video Captioning app settings

| Key | Description |
| --- | --- |
| `display_name` | Name of the app's group in the camera settings. |
| `base_url` | LVC backend. |
| `mediamtx_url` | MediaMTX, for the VAP dashboard's video player. |
| `mqtt_host`, `mqtt_port` | LVC MQTT broker. If `mqtt_host` is empty, VAP does not read captions. |
| `mqtt_tls_enabled`, `mqtt_ca_bundle`, `mqtt_client_cert`, `mqtt_client_key` | TLS to the LVC MQTT broker. |

## How it works

### Registration

On startup, VAP compares its database with the integrations in Nx Witness:

| VAP database | Nx Witness | What VAP does |
| --- | --- | --- |
| No record | No integration | Registers the integration, approves it, and stores the integration user's credentials. Logs `nx_integration_autoregistered`. |
| Record | Integration | Reuses the stored credentials. Logs `nx_integration_already_registered`. |
| No record | Integration | Stops, and logs `nx_integration_exists_in_vms_not_in_db`. |
| Record | No integration | Stops, and logs `nx_integration_exists_in_db_not_in_vms`. |

When it registers, VAP adds to the bundled manifest:

- The object types of each app, from its `label_map` categories and `zones`, so Nx Witness
  accepts the detections.
- A settings group for each app, with its fields: the enable checkbox, **Device**, and
  **Loitering Zone** or **Prompt**.

Registration needs **Accept API Integrations registration requests** turned on in Nx
Witness. Because the object types and the settings are fixed at registration, changing the
selected apps or the `label_map` categories needs a new registration; see
[Register the integration again](#register-the-integration-again).

### Pipeline control from the camera settings

Every 5 seconds, VAP lists the cameras and reads each camera's integration settings. For each
app:

- The checkbox turned on, and no pipeline running: VAP starts one.
- A field changed while the pipeline runs: VAP restarts it with the new values.
- The checkbox turned off: VAP stops the pipeline.

Starting from the camera settings does not need camera discovery in the VAP dashboard.

### Camera streams

VAP gives each pipeline the camera's Nx Witness RTSP URL:

```text
rtsp://<NX_USERNAME>:<NX_PASSWORD>@<NX_HOST>:7001/<device-uuid>?onvif_replay=true
```

### Loitering Detection pipeline

When a pipeline starts, VAP:

1. Sends `POST <DLS base_url>/pipelines/user_defined_pipelines/<pipeline>` to the DL Streamer
   Pipeline Server, with the RTSP URL as source and the device in `detection-properties`.
2. Scales the **Loitering Zone** to the camera's resolution, read from Nx Witness, and sends
   it as `analytics-properties.zones`. Pipelines that declare `roi-properties` also get the
   zone's bounding rectangle as their region of interest.
3. Sends the threshold as `loitering-watermark-properties.loitering-threshold`, to pipelines
   that declare it.
4. Asks the pipeline to publish on `<metadata_topic_prefix>/nx:<device-uuid>`, by default
   `object_tracking/nx:<device-uuid>`.

### Detections

VAP subscribes to `<metadata_topic_prefix>/+`. For each frame, it translates the DL Streamer
metadata into Nx analytics objects and posts them to
`/rest/v4/analytics/engines/<engine>/deviceAgents/<device-uuid>/metadata/object`, as the
integration user. On the first push for a camera, VAP enables the camera's device agent.

Detections reach Nx Witness after the video, because of inference, MQTT and REST latency.
VAP sets how long the Desktop Client keeps drawing each box from the measured latency, within
`metadata_min_duration_ms` and `metadata_max_duration_ms`.

### Bookmarks

Loitering rows (topic `<metadata_topic_prefix>/nx:<device-uuid>/<event_topic_suffix>`) and LVC
captions become bookmarks, posted to `/rest/v4/devices/<device-uuid>/bookmarks`. The bookmark
name is the event or caption text, up to 500 characters, and it lasts 30 seconds.

## Limitations

- **One kind of result per camera view.** The Desktop Client shows either the Object Search
  boxes or the bookmarks in a camera view, not both.
- **Views opened before the pipeline started.** Boxes do not render in a camera view that was
  open before the pipeline started. Close the view, stop and start the pipeline, and open the
  camera again. This is tracked with Network Optix in the
  [developer forum](https://support.networkoptix.com/hc/en-us/community/posts/42656716334871-Analytics-bounding-box-overlay-not-shown-on-live-camera-view-REST-API-based-integration).
- **One bookmark per loitering row.** Loitering events are not throttled: a person who stays
  in the zone adds about one bookmark per second.
- **Settings fixed at registration.** Adding or removing an app, or changing the `label_map`
  categories, needs a new registration.
- **Pipelines are not restarted when an app restarts.** If an analytics app restarts, its
  pipelines stop, but the checkbox stays on. Uncheck and check it again.
- **Digest authentication.** The pipelines need digest authentication for the VAP user.

## Troubleshooting

### VAP and Nx Witness

| Symptom | Cause and fix |
| --- | --- |
| `nx_connect_failed` | VAP cannot reach Nx Witness. Check `NX_HOST`, `NX_USERNAME`, `NX_PASSWORD`, and that port `7001` is reachable from the analytics host. |
| No cameras discovered | Check the checks in [Set Up Nx Witness, Step 6](./set-up-nx-witness.md#step-6-check-nx-witness), and that the user can see the cameras. Check `docker compose logs backend \| grep nx_discover`. |
| `nx_integration_exists_in_vms_not_in_db` | The integration exists in Nx Witness, but VAP's database has no record of it, for example after `docker compose down -v`. [Register the integration again](#register-the-integration-again). |
| `nx_integration_exists_in_db_not_in_vms` | The integration was deleted from Nx Witness. [Register the integration again](#register-the-integration-again). |
| `nx_integration_no_password_in_db` | The stored integration has no password, so VAP cannot push detections. [Register the integration again](#register-the-integration-again). |
| Integration not in **System Administration** → **Integrations** | **Accept API Integrations registration requests** is off; see [Set Up Nx Witness, Step 5](./set-up-nx-witness.md#step-5-accept-api-integration-requests). Turn it on, and [register the integration again](#register-the-integration-again). |
| An app's group is missing from the camera settings | The integration was registered before the app was selected. [Register the integration again](#register-the-integration-again). |

### Pipeline and detections

| Symptom | Cause and fix |
| --- | --- |
| Pipeline fails at once, DL Streamer logs `401 Unauthorized` | Digest authentication is off for the VAP user; see [Set Up Nx Witness, Step 4](./set-up-nx-witness.md#step-4-allow-digest-authentication-for-the-vap-user). |
| Pipeline fails with RTSP connection errors | The Nx Witness host is not reachable from the analytics app. If the host uses a proxy, add `<NX_HOST_IP>` to the app's `no_proxy`. |
| `nx_start_pipeline_failed`, or a connection error to the Pipeline Server | Check `DLS_VISION_HOST` and `DLS_VISION_PORT`, and that the pipeline names in `DLS_PIPELINE_*` exist: `curl -k https://<DLS_VISION_HOST>:<DLS_VISION_PORT>/api/pipelines`. |
| `od_zone_resolution_unavailable` | Nx Witness reports no resolution for the camera, so the pipeline uses its own default zone. |
| No boxes, `mqtt_push_failed` or `nx_push_objects_rejected` in the log | Check that the integration is on for the camera (**Camera Settings** → **Integrations**), and that its credentials are stored (no `nx_integration_no_password_in_db`). |
| No boxes, no MQTT messages | Check that VAP reaches the broker at `MQTT_HOST:MQTT_PORT`, and that the pipeline publishes on `object_tracking/nx:<device-uuid>`: `mosquitto_sub -h <MQTT_HOST> -p <MQTT_PORT> -t 'object_tracking/#' -v`. |
| No boxes, pipeline and MQTT working | Close the camera view, stop and start the pipeline, and open the camera again; see [Limitations](#limitations). |
| No boxes but bookmarks appear, camera has recording on | Stop and start the pipeline to recover. If recording was just enabled for this camera for the first time, also check **Camera Settings** → **Recording** and configure the schedule as desired. A newly enabled schedule is not always configured correctly, and detections are not seen until it is corrected. |
| Boxes labelled `python.detected.object` | The model's labels are not in `label_map`. Add them, run `setup.sh` again, and [register the integration again](#register-the-integration-again). |

### Loitering events and captions

| Symptom | Cause and fix |
| --- | --- |
| No `loitering_event_published` in the log | Check `events_enabled: true`, that `mqtt-table-flattener` runs and its `DEST_TOPIC_SUFFIX` matches `event_topic_suffix`, and that someone has stayed in the zone longer than the threshold. |
| `lvc_mqtt_not_configured_skipping` in the log | `MQTT_BROKER_HOST` is empty, or the configuration was generated before LVC moved its broker settings into the LVC app. Set it, and run `setup.sh` again. |
| LVC form does not render in the dashboard | VAP could not read the LVC schema at startup. Check `curl http://localhost:4173/health`, then `docker compose restart backend`. |
| No captions | Check that the run is active (`curl http://localhost:4173/api/runs`), and the LVC logs for pipeline or RTSP errors. |
| Dashboard video does not play | Check `MEDIAMTX_URL`, and that MediaMTX runs (`curl http://localhost:8889/`). |

### Register the integration again

1. In the Desktop Client, open **Main Menu** → **System Administration** → **Integrations**,
   and remove **VAP Analytics Integration**.
2. Delete VAP's record of it:

   ```bash
   docker compose exec postgres psql -U vms -d vms_plugin -p 5434 \
     -c "DELETE FROM nx_analytics_integrations WHERE vms_name = 'nx-main';"
   ```

   Use your `PG_USER` and `PG_PORT` if you changed them.

3. Restart the backend:

   ```bash
   docker compose restart backend
   ```

VAP registers the integration again, and logs `nx_integration_autoregistered`. Turn the
integration on again for each camera.

## References

- [Nx Witness Ubuntu installation guide](https://support.networkoptix.com/hc/en-us/articles/360010535793-Ubuntu-Linux-OS-Installation-Guide)
- [How secure is Nx Witness](https://support.networkoptix.com/hc/en-us/articles/115011970028-How-secure-is-Nx-Witness)
- [Loitering Detection documentation](https://docs.openedgeplatform.intel.com/dev/edge-ai-suites/loitering-detection/index.html)
- [Live Video Captioning Get Started Guide](https://docs.openedgeplatform.intel.com/dev/edge-ai-suites/live-video-captioning/get-started.html)
