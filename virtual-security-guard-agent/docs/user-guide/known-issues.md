<!--hide_directive
```{eval-rst}
.. meta::
   :description: Troubleshooting guidance for the Virtual Security Guard Agent console.
   :keywords: Virtual Security Guard, troubleshooting, VSS, Hermes.
```
hide_directive-->

<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Known Issues

## Hermes or VSS Service Shows "Unreachable"

Symptoms:

- The sidebar or **Settings** page shows **Hermes** or **VSS**
  service as not reachable; searches never start.

Checks:

- Run the health probes on the VSG host:

  ```bash
  for u in /healthz /hermes/health /vss/manager/health; do
    printf '%-22s %s\n' "$u" "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:12346$u)"
  done
  ```

- `502` or `504`: The upstream is down, or `HERMES_BASE_URL` or `VSS_BASE_URL` in
  `deploy/.env` is incorrect. Run `make logs` to see the NGINX server errors.
  If you fix the base URL, run `make up` to recreate the container.
- `401` on Hermes: `HERMES_API_KEY` does not match the Hermes
  `API_SERVER_KEY`.
- Behind a proxy: Add the Hermes and VSS hosts to `no_proxy`.

## The VSG Agent Replies but the Console Shows No Grid

Symptoms:

- The VSG agent answers in text, but no review grid, report, or status widget appears.

Details:

- The console only renders fenced `vsg-*` blocks. If the Hermes skills are
  missing or out of date, the VSG agent answers in plain text.

- Smaller models can make this problem more persistent because they have weaker
  tool-calling capabilities.

Checks:

- Reinstall the skills on the Hermes host and start a new session. See
  [Install the VSG agent skills](./get-started/set-up-prerequisite-stack.md#5-install-the-vsg-agent-skills).
- Check that **Settings → Directive protocol** matches the installed skill.
- Use a model with stronger tool-calling capabilities.

## The VSG Agent Never Searches or Writes the Tool Call as Text

Symptoms:

- The VSG agent replies without running `vss_search_video`, or the reply contains a
  tool call written out as text or JSON.

Details:

- OpenVINO™ model server returns structured `tool_calls` only when the model's tool
  parser is
  set. If the graph does not set the tool parser, add
  `tool_parser` and `reasoning_parser` to the LLM node in the model's
  `graph.pbtxt`, using the values on the model card. Then restart the model
  server with `docker restart agent-harness-install-ovms`.

Checks:

- Check which parsers the OpenVINO™ model server chose:
  `docker logs agent-harness-install-ovms 2>&1 | grep -E 'tool_parser|reasoning_parser'`.
- Check that `hermes tools` keeps the `vss` MCP tools for the API server, and
  that `mcp_servers.vss` in `~/.hermes/config.yaml` points at the VSS MCP
  server.

## The VSG Agent Ignores Its Workflow or Uses Other Skills

Symptoms:

- Replies do not follow the search → review → trace flow, or mention skills
  that are not the VSG agent's.

Details:

- The Hermes installation loads every skill under `~/.hermes/skills`. Its
  installer adds bundled skills, and `hermes update` can add them again.

Checks:

- Run `hermes skills list` on the Hermes host. If it lists anything other
  than `virtual-security-guard` and `vsg-incident-report`, run
  `make install-skills INSTALL_ARGS=--exclusive` and start a new session.

## Grid Shows "Couldn't read the search results"

Symptoms:

- A VSG agent reply shows an error with a **Retry** button instead of matches.

Details:

- The console could not read the Hermes session transcript after the run.
  Click **Retry** once Hermes is reachable. The console never falls back to
  clips the model wrote.

## Route or Floorplan Shows No Camera

Symptoms:

- Sightings are confirmed but nothing is drawn on the floorplan.

Checks:

- The camera's VSS tag must be a camera key on the plan. The Floorplan header
  lists VSS tags that are not on the plan; add them to the file. See
  [Configure the Floorplan](./how-to-guides/configure-floorplan.md).

## Times Look Shifted

Details:

- The VSS host and browser may use different clocks or time zones. Sightings
  are ordered by VSS time, not the browser clock. Keep the VSS host clock
  synchronized using the Network Time Protocol (NTP).

## Live Search Does Not Find Anything

Checks:

- Live search watches only cameras on the **Live cameras** page. Ensure
  the  Real-Time Streaming Protocol (RTSP) streams are added and ingesting.
- RTSP hosts must be reachable from the VSS host (add them to `no_proxy`).
- The watch stops after the time limit or quiet period set on the **Settings** page.

## Reports Disappear After Reload

Details:

- Generated PDFs are kept in browser memory for the open tab only. Use
  **Reports → Open in Argus** to open a past investigation in the console’s Argus
  page, then generate the PDF again from Argus’s report draft.

## Floorplan and Settings Are Per Browser

Details:

- The uploaded floorplan and the investigation settings are stored in the
  browser. Upload the plan again on another browser, or use
  **Settings → Clear local data** to reset.

## Port Conflicts

If the console is unreachable, check whether another service is using port
`12346`. If so, set `VSG_UI_PORT` in `deploy/.env` to an available port.