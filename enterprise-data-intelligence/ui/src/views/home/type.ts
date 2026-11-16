// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

export interface KnowledgeBaseSummary {
  id: string;
  name: string;
  description?: string;
  updatedAt: string;
}

export interface DocumentItem {
  id: string;
  name: string;
  type: string;
  size: string;
  updatedAt: string;
}

export interface KnowledgeBaseDetail {
  id: string;
  name: string;
  description: string;
  documents: DocumentItem[];
}

export type AssistantBlockKind = "agent";
export type AssistantAgentLevel = "main" | "sub" | "none";

export interface AssistantBlock {
  id: string;
  kind: AssistantBlockKind;
  agentLevel: AssistantAgentLevel;
  title: string;
  content: string;
  isCompleted: boolean;
  isToolActive?: boolean;
}

export interface UserChatMessage {
  role: "user";
  content: string;
}

export interface AssistantChatMessage {
  role: "assistant";
  content: string;
  isCompleted: boolean;
  blocks: AssistantBlock[];
}

export type ChatMessage = UserChatMessage | AssistantChatMessage;

export interface StreamDisplayEvent {
  kind: AssistantBlockKind;
  blockId: string;
  agentLevel: AssistantAgentLevel;
  title: string;
  content: string;
  replace?: boolean;
  done?: boolean;
  isToolActive?: boolean;
}
