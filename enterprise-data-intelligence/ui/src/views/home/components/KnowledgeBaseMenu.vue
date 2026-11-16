<!--
  Copyright (C) 2026 Intel Corporation
  SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div class="knowledge-menu" :class="{ collapsed: props.collapsed }">
    <div v-show="props.collapsed" class="collapsed-rail">
      <span
        class="rail-action"
        :title="expandLabel"
        @click="handleCollapseToggle"
      >
        <MenuUnfoldOutlined />
      </span>

      <button
        v-if="showAssetLibrary"
        type="button"
        class="rail-category"
        :title="knowledgeCategory.title"
        @click="handleCollapsedCategoryClick('knowledge')"
      >
        <span class="rail-category-icon">
          <SvgIcon :name="knowledgeCategory.icon" inherit />
        </span>
        <span class="rail-category-label">{{ knowledgeCategory.title }}</span>
      </button>

      <button
        type="button"
        class="rail-category"
        :title="monitorCategory.title"
        @click="handleCollapsedCategoryClick('monitor')"
      >
        <span class="rail-category-icon">
          <SvgIcon :name="monitorCategory.icon" inherit />
        </span>
        <span class="rail-category-label">{{ monitorCategory.title }}</span>
      </button>
    </div>

    <div v-show="!props.collapsed" class="menu-shell">
      <div class="menu-header">
        <div class="menu-title-row">
          <div class="menu-copy">
            <div class="menu-title">{{ menuTitle }}</div>
            <div class="menu-description">{{ menuDescription }}</div>
          </div>
          <span
            class="menu-action"
            :title="collapseLabel"
            @click="handleCollapseToggle"
          >
            <MenuFoldOutlined />
          </span>
        </div>
      </div>

      <div class="menu-wrapper">
        <section
          v-if="showAssetLibrary"
          class="category-section"
          :class="{ expanded: isKnowledgeExpanded }"
        >
          <button
            type="button"
            class="category-header"
            @click="toggleCategory('knowledge')"
          >
            <span class="category-icon">
              <SvgIcon :name="knowledgeCategory.icon" inherit :size="24" />
            </span>
            <span class="category-copy">
              <span class="category-title">{{ knowledgeCategory.title }}</span>
              <span class="category-description">{{
                knowledgeCategory.description
              }}</span>
            </span>
            <CaretRightOutlined
              :class="['toggle-arrow', { open: isKnowledgeExpanded }]"
            />
          </button>

          <div v-show="isKnowledgeExpanded" class="category-body">
            <a-empty
              v-show="!knowledgeCategory.items.length"
              class="intel-empty-normal category-empty"
              :description="t('libraryMenu.empty')"
            />

            <article
              v-for="entry in knowledgeCategory.items"
              :key="entry.id"
              class="entry-card"
            >
              <div class="entry-header">
                <div class="entry-copy">
                  <div class="entry-title">{{ entry.name }}</div>
                </div>

                <div class="entry-side">
                  <span
                    class="entry-count"
                    :title="t('libraryMenu.meta.files')"
                  >
                    {{ entry.asset_count }}
                  </span>
                  <a-checkbox
                    :checked="activatedLibraryNames.includes(entry.name)"
                    :disabled="isUpdatingLibraries"
                    :aria-label="entry.name"
                    @change="handleKnowledgeEntryCheckChange(entry, $event)"
                  />
                </div>
              </div>
            </article>
          </div>
        </section>
        <section
          class="category-section"
          :class="{ expanded: isMonitorExpanded }"
        >
          <button
            type="button"
            class="category-header"
            @click="toggleCategory('monitor')"
          >
            <span class="category-icon">
              <SvgIcon :name="monitorCategory.icon" inherit :size="24" />
            </span>
            <span class="category-copy">
              <span class="category-title">{{ monitorCategory.title }}</span>
              <span class="category-description">{{
                monitorCategory.description
              }}</span>
            </span>
            <CaretRightOutlined
              :class="['toggle-arrow', { open: isMonitorExpanded }]"
            />
          </button>

          <div v-show="isMonitorExpanded" class="category-body">
            <a-empty
              v-show="!monitorCategory.items.length"
              class="intel-empty-normal category-empty"
              :description="t('libraryMenu.empty')"
            />

            <article
              v-for="entry in monitorCategory.items"
              :key="entry.path"
              class="simple-entry-card monitor-entry-card"
            >
              <div class="simple-entry-top">
                <div class="entry-copy">
                  <div class="entry-title">{{ entry.name }}</div>
                </div>
              </div>

              <div class="monitor-detail-list">
                <div class="monitor-detail-item monitor-detail-compact-item">
                  <span class="simple-meta-label">
                    {{ t("libraryMenu.meta.fileType") }} /
                    {{ t("libraryMenu.meta.size") }}
                  </span>
                  <span class="monitor-compact-value">
                    {{ entry.type }} / {{ entry.size || "--" }}
                  </span>
                </div>
                <div class="monitor-detail-item">
                  <span class="simple-meta-label">{{
                    t("libraryMenu.meta.path")
                  }}</span>
                  <span class="monitor-path-value" :title="entry.path">
                    {{ entry.path }}
                  </span>
                </div>
              </div>
            </article>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  CaretRightOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons-vue";
import {
  getLibraryList,
  getActivatedLibraries,
  getMonitorFolderList,
  requestLibraryUpdate,
} from "@/api/knowledgeBase";
import type { Library } from "@/api/knowledgeBase";
import { useI18n } from "vue-i18n";

type KnowledgeEntry = Library;

interface MonitorEntry {
  name: string;
  type: string;
  size: string | number;
  path: string;
}

type LibrarySource = "knowledge" | "monitor" | "media";

interface LibraryCategory<T> {
  id: LibrarySource;
  title: string;
  description: string;
  icon: any;
  items: T[];
}

const props = withDefaults(
  defineProps<{
    collapsed?: boolean;
  }>(),
  {
    collapsed: false,
  },
);

const emit = defineEmits(["toggle-collapse", "request-expand"]);
const { t } = useI18n();
const showAssetLibrary = false;

const knowledgeEntries = ref<KnowledgeEntry[]>([]);
const activatedLibraryNames = ref<string[]>([]);
const isUpdatingLibraries = ref(false);
const monitorEntries = ref<MonitorEntry[]>([]);
const expandedCategoryIds = ref<LibrarySource[]>([]);

const expandLabel = computed(() => t("libraryMenu.expandSidebar"));
const collapseLabel = computed(() => t("libraryMenu.collapseSidebar"));
const menuTitle = computed(() => t("libraryMenu.title"));
const menuDescription = computed(() => t("libraryMenu.description"));

const knowledgeCategory = computed<LibraryCategory<KnowledgeEntry>>(() => ({
  id: "knowledge",
  title: t("libraryMenu.category.knowledgeTitle"),
  description: t("libraryMenu.category.knowledgeDescription"),
  icon: "icon-knowledge-base1",
  items: knowledgeEntries.value,
}));

const monitorCategory = computed<LibraryCategory<MonitorEntry>>(() => ({
  id: "monitor",
  title: t("libraryMenu.category.monitorTitle"),
  description: t("libraryMenu.category.monitorDescription"),
  icon: "icon-work-directory",
  items: monitorEntries.value,
}));

const isCategoryExpanded = (categoryId: LibrarySource) => {
  return expandedCategoryIds.value.includes(categoryId);
};

const isKnowledgeExpanded = computed(() => isCategoryExpanded("knowledge"));
const isMonitorExpanded = computed(() => isCategoryExpanded("monitor"));

const toggleCategory = (categoryId: LibrarySource) => {
  expandedCategoryIds.value = expandedCategoryIds.value.includes(categoryId)
    ? expandedCategoryIds.value.filter((id) => id !== categoryId)
    : [...expandedCategoryIds.value, categoryId];
};

const queryActivatedLibraries = async () => {
  const response = await getActivatedLibraries();
  activatedLibraryNames.value = response.asset_libraries;
  return response.asset_libraries;
};

const handleKnowledgeEntryCheckChange = async (
  entry: KnowledgeEntry,
  event: { target: { checked: boolean } },
) => {
  if (isUpdatingLibraries.value) return;
  const checked = event.target.checked;
  isUpdatingLibraries.value = true;
  try {
    const currentNames = await queryActivatedLibraries();
    const nextNames = checked
      ? [...new Set([...currentNames, entry.name])]
      : currentNames.filter((name) => name !== entry.name);
    await requestLibraryUpdate({
      asset_libraries: nextNames,
    });
    await queryActivatedLibraries();
  } catch {
    return;
  } finally {
    isUpdatingLibraries.value = false;
  }
};

const handleCollapseToggle = () => {
  emit("toggle-collapse", !props.collapsed);
};

const handleCollapsedCategoryClick = (categoryId: LibrarySource) => {
  expandedCategoryIds.value = [categoryId];
  emit("request-expand", categoryId);
  emit("toggle-collapse", false);
};

const queryKnowledgeEntries = async () => {
  const [libraries, selection]: [
    KnowledgeEntry[],
    { asset_libraries: string[] },
  ] = await Promise.all([getLibraryList(), getActivatedLibraries()]);
  activatedLibraryNames.value = selection.asset_libraries;
  knowledgeEntries.value = libraries;
};

const queryWorkSpace = async () => {
  const response: any = await getMonitorFolderList({
    filepath: ".openclaw/workspace",
  });
  monitorEntries.value = response?.items || [];
};

onMounted(() => {
  if (showAssetLibrary) {
    queryKnowledgeEntries();
  }
  queryWorkSpace();
});
</script>

<style scoped lang="less">
.knowledge-menu {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--surface-panel-bg, var(--bg-card-color)) 96%, white)
      0%,
    color-mix(in srgb, var(--bg-card-color) 94%, white) 100%
  );
}

.knowledge-menu.collapsed {
  background: color-mix(in srgb, var(--bg-card-color) 96%, white);
}

.menu-shell {
  .flex-column;
  height: 100%;
}

.collapsed-rail {
  height: 100%;
  .flex-column;
  align-items: center;
  gap: 10px;
  padding: 14px 10px;
}

.rail-action,
.menu-action {
  padding: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: var(--font-text-color);
  font-size: var(--font-size-16);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  top: -8px;

  &:hover {
    color: var(--color-primary);
    background: var(--surface-card-bg-hover);
  }
}

.rail-action {
  border: 1px solid var(--border-main-color);
}

.rail-category {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 6px;
  border: 1px solid color-mix(in srgb, var(--border-primary) 60%, transparent);
  border-radius: 16px;
  background: color-mix(in srgb, var(--surface-card-bg) 82%, white);
  color: var(--font-main-color);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    background: var(--surface-card-bg-hover);
    border-color: var(--color-primary-second);
  }
}

.rail-category-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--color-primaryBg);
  color: var(--color-primary);
  font-size: var(--font-size-16);
}

.rail-category-label {
  font-size: var(--font-size-11);
  font-weight: 600;
  color: var(--font-main-color);
  line-height: 1.2;
  text-align: center;
}

.menu-header {
  padding: 12px 14px 10px;
  border-bottom: 1px solid
    color-mix(in srgb, var(--border-main-color) 80%, transparent);
}

.menu-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.menu-copy {
  min-width: 0;
}

.menu-title {
  font-size: var(--font-size-16);
  font-weight: 700;
  color: var(--font-main-color);
  line-height: 1.3;
}

.menu-description {
  margin-top: 6px;
  font-size: var(--font-size-12);
  line-height: 1.5;
  color: var(--font-tip-color);
}

.menu-wrapper {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.category-section {
  padding: 1px;
  border: 1px solid
    color-mix(in srgb, var(--border-primary) 18%, var(--border-main-color) 82%);
  border-radius: 18px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--surface-panel-bg) 88%, white) 0%,
    color-mix(in srgb, var(--bg-content-color) 96%, white) 100%
  );
}

.category-section.expanded {
  border-color: color-mix(
    in srgb,
    var(--color-primary) 18%,
    var(--border-main-color) 78%
  );
  box-shadow: 0 8px 18px
    color-mix(in srgb, var(--color-primary) 8%, transparent);
}

.category-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 13px;
  border: none;
  border-radius: 16px 16px 0 0;
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--color-primaryBg) 40%, white) 0%,
    color-mix(in srgb, var(--surface-card-bg) 72%, white) 100%
  );
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.2s ease,
    box-shadow 0.2s ease;

  &:hover {
    background: linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-primaryBg) 52%, white) 0%,
      color-mix(in srgb, var(--surface-card-bg-hover) 80%, white) 100%
    );
  }
}

.category-section.expanded .category-header {
  box-shadow: inset 0 -1px 0
    color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.category-icon {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--color-primaryBg) 92%, white),
    color-mix(in srgb, var(--surface-card-bg) 82%, white)
  );
  color: var(--color-primary);
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px
    color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.category-copy {
  min-width: 0;
  flex: 1;
  .flex-column;
  gap: 2px;
}

.category-title {
  font-size: var(--font-size-15);
  font-weight: 700;
  color: var(--font-main-color);
  letter-spacing: 0.01em;
}

.category-description {
  font-size: var(--font-size-12);
  color: var(--font-tip-color);
  line-height: 1.45;
}

.toggle-arrow {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-primaryBg) 76%, white);
  font-size: var(--font-size-12);
  color: var(--color-primary);
  transition: transform 0.2s ease;

  &.open {
    transform: rotate(90deg);
  }
}

.category-body {
  .flex-column;
  gap: 10px;
  padding: 10px 11px 11px;

  :deep(.intel-empty.intel-empty-normal .intel-empty-image) {
    height: 64px;
  }
}

.category-empty {
  padding: 2px 0 0;
}

.category-empty:deep(.ant-empty-description) {
  font-size: var(--font-size-12);
}

.simple-entry-card {
  padding: 12px;
  border-radius: 14px;
  border: 1px solid
    color-mix(in srgb, var(--border-main-color) 82%, transparent);
  background: color-mix(in srgb, var(--surface-card-bg) 90%, white);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.simple-entry-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.simple-entry-description {
  margin-top: 4px;
  font-size: var(--font-size-12);
  line-height: 1.45;
  color: var(--font-tip-color);
  word-break: break-word;
}

.simple-entry-count {
  flex-shrink: 0;
}

.media-detail-list,
.monitor-detail-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.media-detail-item,
.monitor-detail-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.media-detail-inline-item {
  align-items: flex-start;
}

.monitor-detail-compact-item {
  align-items: flex-start;
}

.monitor-compact-value {
  font-size: var(--font-size-12);
  line-height: 1.45;
  color: var(--font-text-color);
}

.monitor-path-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: var(--font-size-12);
  line-height: 1.45;
  color: var(--font-text-color);
  text-align: left;
  text-overflow: ellipsis;
  direction: rtl;
  white-space: nowrap;
}

.monitor-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: var(--font-size-11);
  font-weight: 700;
}

.monitor-status-badge.success {
  background: color-mix(in srgb, var(--color-successSoft) 76%, white);
  color: var(--color-success);
}

.monitor-status-badge.muted {
  background: color-mix(in srgb, var(--surface-card-bg-hover) 72%, white);
  color: var(--font-tip-color);
}

.simple-meta-label,
.simple-meta-value {
  font-size: var(--font-size-11);
  line-height: 1.2;
}

.simple-meta-label {
  opacity: 0.72;
}

.simple-meta-value {
  color: inherit;
  .single-ellipsis;
}

.entry-card {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid
    color-mix(in srgb, var(--border-main-color) 82%, transparent);
  background: color-mix(in srgb, var(--surface-card-bg) 86%, white);
}

.entry-header {
  .flex-between;
  gap: 10px;
}

.entry-copy {
  min-width: 0;
  flex: 1;
}

.entry-title {
  font-size: var(--font-size-13);
  font-weight: 700;
  color: var(--font-text-color);
  line-height: 1.4;
}

.entry-side {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.entry-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface-panel-bg) 78%, white);
  font-size: var(--font-size-11);
  font-weight: 700;
  color: var(--font-main-color);
}
</style>
