<!--hide_directive
```{eval-rst}
.. meta::
   :description: Run unit tests for the Virtual Security Guard Agent user interface.
   :keywords: Virtual Security Guard Agent, tests, Vitest, GNU Make, Node.js
```
hide_directive-->

<!--
SPDX-FileCopyrightText: (C) 2026 Intel Corporation
SPDX-License-Identifier: Apache-2.0
-->

# Run Unit Tests


Run the following commands from the `virtual-security-guard-agent` application
directory to test the UI with the [Vitest framework](https://vitest.dev/).

## Prerequisites
- GNU Make tool
- Node.js 22 runtime.

```bash
make install        # once: npm ci
make check          # lint + type-check + unit tests
make lint           # lint + type-check only
make test           # unit tests only
make format         # format the sources with Prettier
```