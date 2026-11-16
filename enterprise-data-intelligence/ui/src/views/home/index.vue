<!--
  Copyright (C) 2026 Intel Corporation
  SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div class="home-layout">
    <aside
      ref="knowledgePaneRef"
      class="knowledge-pane"
      :class="{ collapsed: isKnowledgePaneCollapsed }"
      :style="knowledgePaneStyle"
    >
      <KnowledgeBaseMenu
        :collapsed="isKnowledgePaneCollapsed"
        @toggle-collapse="handleKnowledgePaneCollapse"
        @request-expand="expandKnowledgePane"
      />

      <button
        v-if="!isKnowledgePaneCollapsed"
        type="button"
        class="knowledge-resize-handle"
        aria-label="Resize knowledge pane"
        @mousedown="startKnowledgeResize"
      ></button>
    </aside>

    <section class="chat-pane">
      <Chatqna />
    </section>

    <button
      v-if="!isMonitorOpen"
      class="monitor-trigger"
      type="button"
      :title="t('monitor.title')"
      @click="openMonitor"
    >
      <span class="monitor-trigger-icon">
        <BarChartOutlined />
      </span>
    </button>

    <aside class="monitor-pane" :class="{ open: isMonitorOpen }">
      <TokenSaving embedded embedded-closable @close="closeMonitor" />
    </aside>
  </div>
</template>

<script setup lang="ts">
import { BarChartOutlined } from "@ant-design/icons-vue";
import { useI18n } from "vue-i18n";
import TokenSaving from "@/components/TokenSaving.vue";
import { Chatqna, KnowledgeBaseMenu } from "./components/index";

const { t } = useI18n();
const isMonitorOpen = ref(false);
const knowledgePaneRef = ref<HTMLElement | null>(null);
const isKnowledgePaneCollapsed = ref(false);
const knowledgePaneWidth = ref(320);
const isKnowledgePaneResizing = ref(false);
const knowledgePaneLeft = ref(0);

const KNOWLEDGE_PANE_COLLAPSED_WIDTH = 88;
const KNOWLEDGE_PANE_MIN_WIDTH = 280;
const KNOWLEDGE_PANE_MAX_WIDTH = 420;

const knowledgePaneStyle = computed(() => {
  const width = isKnowledgePaneCollapsed.value
    ? KNOWLEDGE_PANE_COLLAPSED_WIDTH
    : knowledgePaneWidth.value;

  return {
    width: `${width}px`,
    minWidth: `${width}px`,
    flexBasis: `${width}px`,
  };
});

const openMonitor = () => {
  isMonitorOpen.value = true;
};

const closeMonitor = () => {
  isMonitorOpen.value = false;
};

const handleKnowledgePaneCollapse = (collapsed: boolean) => {
  isKnowledgePaneCollapsed.value = collapsed;
};

const expandKnowledgePane = () => {
  isKnowledgePaneCollapsed.value = false;
};

const handleKnowledgePaneResize = (event: MouseEvent) => {
  if (!isKnowledgePaneResizing.value) {
    return;
  }

  const nextWidth = Math.min(
    KNOWLEDGE_PANE_MAX_WIDTH,
    Math.max(KNOWLEDGE_PANE_MIN_WIDTH, event.clientX - knowledgePaneLeft.value),
  );

  knowledgePaneWidth.value = nextWidth;
};

const stopKnowledgeResize = () => {
  if (!isKnowledgePaneResizing.value) {
    return;
  }

  isKnowledgePaneResizing.value = false;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
};

const startKnowledgeResize = (event: MouseEvent) => {
  if (isKnowledgePaneCollapsed.value) {
    return;
  }

  knowledgePaneLeft.value =
    knowledgePaneRef.value?.getBoundingClientRect().left || 0;
  isKnowledgePaneResizing.value = true;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
  event.preventDefault();
};

onMounted(() => {
  window.addEventListener("mousemove", handleKnowledgePaneResize);
  window.addEventListener("mouseup", stopKnowledgeResize);
});

onUnmounted(() => {
  window.removeEventListener("mousemove", handleKnowledgePaneResize);
  window.removeEventListener("mouseup", stopKnowledgeResize);
  stopKnowledgeResize();
});
</script>
<style scoped lang="less">
.home-layout {
  position: relative;
  height: 100%;
  min-height: 0;
  display: flex;
  padding: 12px;
  overflow: hidden;
  background: var(--bg-content-color);
}

.knowledge-pane,
.chat-pane,
.monitor-pane {
  min-height: 0;
  height: 100%;
}

.knowledge-pane {
  position: relative;
  box-sizing: border-box;
  flex: 0 0 auto;
  overflow: hidden;
  padding-right: 12px;
  border-radius: 24px;
  background: var(--bg-card-color);
  border: 1px solid
    color-mix(in srgb, var(--border-primary) 38%, var(--border-main-color) 62%);
  box-shadow: 0 8px 24px var(--bg-box-shadow);
  margin-right: 12px;
  transition:
    width 0.22s ease,
    min-width 0.22s ease,
    flex-basis 0.22s ease,
    box-shadow 0.2s ease;
}

.knowledge-pane.collapsed {
  padding-right: 0;
  box-shadow: 0 8px 18px
    color-mix(in srgb, var(--bg-box-shadow) 82%, transparent);
}

.knowledge-resize-handle {
  position: absolute;
  top: 16px;
  right: 0;
  bottom: 16px;
  width: 12px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: col-resize;
  z-index: 2;

  &::before {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 4px;
    height: 44px;
    border-radius: 999px;
    transform: translate(-50%, -50%);
    background: color-mix(in srgb, var(--border-primary) 78%, transparent);
    transition: background 0.2s ease;
  }

  &:hover::before {
    background: var(--color-primary-second);
  }
}

.chat-pane {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  border-radius: 24px;
  background: var(--bg-content-color);
  box-shadow: 0 8px 24px var(--bg-box-shadow);
  transition: width 0.24s ease;
}

.monitor-pane {
  position: relative;
  width: 0;
  min-width: 0;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
  transition:
    width 0.24s ease,
    opacity 0.2s ease;
}

.monitor-pane.open {
  width: 360px;
  opacity: 1;
  pointer-events: auto;
  margin-left: 12px;
}

.monitor-trigger {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 20;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 68px;
  padding: 0;
  border: 1px solid
    color-mix(in srgb, var(--color-primary) 18%, var(--color-white) 82%);
  border-right: none;
  border-radius: 16px 0 0 16px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.98) 0%,
    color-mix(in srgb, var(--color-primaryBg) 24%, var(--color-white) 76%) 100%
  );
  color: var(--color-primary);
  box-shadow: -10px 14px 30px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(14px);
  cursor: pointer;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease,
    background 0.2s ease;
}

.monitor-trigger::before {
  content: "";
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(
    180deg,
    var(--color-primary-hover) 0%,
    var(--color-primary) 100%
  );
  opacity: 0.9;
}

.monitor-trigger:hover {
  transform: translateY(-50%) translateX(-4px);
  border-color: color-mix(
    in srgb,
    var(--color-primary) 34%,
    var(--color-white) 66%
  );
  background: linear-gradient(
    180deg,
    var(--color-primaryBg) 0%,
    color-mix(in srgb, var(--color-primaryBg) 34%, var(--color-white) 66%) 100%
  );
  color: var(--color-primary-hover);
  box-shadow: 0 12px 24px
    color-mix(in srgb, var(--bg-box-shadow) 100%, transparent);
}

.monitor-trigger-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding-left: 3px;
  font-size: 18px;
  line-height: 1;
}

@media (max-width: 1280px) {
  .home-layout {
    padding-right: 12px;
  }

  .knowledge-pane {
    max-width: 280px;
  }

  .monitor-pane {
    position: absolute;
    top: 12px;
    right: 12px;
    bottom: 12px;
    width: min(360px, calc(100vw - 24px));
    transform: translateX(calc(100% + 12px));
    opacity: 0;
    pointer-events: none;
    transition:
      transform 0.24s ease,
      opacity 0.2s ease;
  }

  .monitor-pane.open {
    width: min(360px, calc(100vw - 24px));
    transform: translateX(0);
    opacity: 1;
    pointer-events: auto;
  }

  .monitor-trigger {
    right: 0;
  }
}

@media (max-width: 768px) {
  .knowledge-pane {
    display: none;
  }

  .monitor-trigger {
    width: 38px;
    height: 62px;
  }
}
</style>
