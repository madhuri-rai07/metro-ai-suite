// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

import request from "../request";
const LIBRARY_API = "/library-api";
const APP_API = "/app-api";
const METRICS_API = "/metrics-api";
const WORKSPACE_API = "/workspace-api";

export interface Library {
  id: string;
  name: string;
  asset_count: number;
}

export const getLibraryList = () => {
  return request({
    url: `${LIBRARY_API}/v1/libraries`,
    method: "get",
  }) as Promise<Library[]>;
};

export const getActivatedLibraries = () => {
  return request({
    url: `${APP_API}/v1/libraries/selection`,
    method: "get",
  }) as Promise<{ asset_libraries: string[] }>;
};

export const requestLibraryUpdate = (data: { asset_libraries: string[] }) => {
  return request({
    url: `${APP_API}/v1/libraries/selection`,
    method: "patch",
    data,
    showLoading: true,
  });
};

export const getMonitorFolderList = (params: Object) => {
  return request({
    url: `${WORKSPACE_API}/v1/media`,
    method: "get",
    params,
  });
};

export const getTokenStats = () => {
  return request({
    url: `${METRICS_API}/v1/metrics`,
    method: "get",
  });
};

export const requestTokenRest = () => {
  return request({
    url: `${METRICS_API}/v1/metrics/reset`,
    method: "post",
    showLoading: true,
    showSuccessMsg: true,
    successMsg: "monitor.resetSuccess",
  });
};
