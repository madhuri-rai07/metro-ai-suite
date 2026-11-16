<!--hide_directive
```{eval-rst}
.. meta::
    :description: Hardware, software, and network requirements for the Virtual Security Guard Agent.
    :keywords: Virtual Security Guard Agent, system requirements, hardware, software, VSS, Hermes
```
hide_directive-->

<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# System Requirements

The VSG agent console container has light resource requirements.

VSS and the model used by the VSG agent on the Hermes agent server account
for most compute needs. Consult their respective documentation for sizing
details.

## Validated Platforms

- **Hardware**: VSS and the OpenVINO™ model server run on Intel® Xeon®
  or Intel® Core™ Ultra Series 3 platforms, or an Intel® Arc™ B70 discrete GPU.
  The VSG container can run on the VSS host or any host that can reach both
  Hermes API server and the VSS gateway.
- **Reasoning model**: an OpenVINO™ model on OpenVINO™ model server that returns tool calls.
  The
  GPU (or system memory for an integrated GPU) must accommodate the weights,
  key-value (KV) cache, and any VSS models on the same host.
- **OS**: Ubuntu OS version 24.04 LTS.

## VSG Container

| Resource | Value |
|---|---|
| CPU | 1 core (Compose limit) |
| Memory | 256 MB (Compose limit) |
| Disk | About 120 MB for the image; allow 1 GB to build it locally. |

## Model Host (Hermes Agent Server and OpenVINO Model Server)

The reasoning model has the largest resource requirements for the VSG agent.
These values are the minimum requirements for the default model,
`OpenVINO/Qwen3.6-35B-A3B-int4-ov`, and are a starting point, not a guarantee of
performance or accuracy.

| Resource | Minimum |
|---|---|
| Processor | Intel® Core™ Ultra Series 3 processor with an integrated GPU. Validated on Panther Lake (PTL 358H). The integrated GPU uses system RAM. |
| Memory | 64 GB RAM. The weights, key-value cache, and any VSS models on the same host share the system memory. |
| Disk | 128 GB free for the model weights and Hugging Face cache. |

- A model running on an integrated GPU responds more slowly than a hosted model.
  Expect each reply to take several seconds to a few minutes. The first request
  after a restart takes the longest because the system loads the model and
  processes the prompt.
- Smaller models, such as models with 9 billion parameters, respond faster but
  are more likely to ignore the reply format or call tools incorrectly. Use
  them to try the VSG agent, but not for critical investigations.
- Larger dense models require more memory and run slowly on a CPU or an
  integrated GPU. Use them only on a host with enough memory and, ideally, a
  GPU with enough dedicated memory.
- Other hardware is untested. Check the reply speed on your host before relying on
  that hardware.

## Software

- Docker Engine with the Docker Compose tool and Docker Buildx plugin:
  [Docker Engine on Ubuntu OS](https://docs.docker.com/engine/install/ubuntu/).
  Building the UI image requires the BuildKit builder backend. Docker Compose tool
  uses this backend only when the Docker Buildx plugin is installed. Check for the
  plugin with `docker buildx version`.
- GNU Make tool: `sudo apt-get install -y make`.
- A VSS deployment with search enabled, the VSS Model Context Protocol (MCP)
  server, and indexed footage.
- A Hermes agent server with the API server enabled and the VSS MCP server
  registered.
  See [Set Up the Prerequisite Stack](./set-up-prerequisite-stack.md) to set up VSS,
  then use the `agent-harness-install` to configure the Hermes agent server,
  OpenVINO model server, and Inference Router.

## Network Ports

| Port | Service | Reached by |
|---|---|---|
| `12346` | VSG agent console (`VSG_UI_PORT`) | The browser needs only this port. |
| `8642` | Hermes API server | The VSG container. |
| `12345` | VSS NGINX gateway, including the VSS MCP server at `/mcp` | The VSG container and the Hermes agent server. |
| `8010` | Inference Router, on the `<HOST_IP>` given to the installer | Hermes agent server, on the same host. |
| `8450` (`HARNESS_OVMS_REST_PORT`) | OpenVINO model server, on the `<HOST_IP>` given to the installer | The Inference Router. |