<!--
  Copyright (C) 2026 Intel Corporation
  SPDX-License-Identifier: Apache-2.0
-->

<template>
  <div class="connection-screen">
    <div class="connection-intro">
      <div class="connection-heading">
        <span class="connection-icon"><ApiOutlined /></span>
        <div class="connection-heading-copy">
          <span class="connection-eyebrow">{{
            $t("chat.gateway.eyebrow")
          }}</span>
          <h1>{{ $t("chat.gateway.title") }}</h1>
        </div>
      </div>
      <p>{{ $t("chat.gateway.description") }}</p>
    </div>
    <form class="connection-form" @submit.prevent="emit('connect')">
      <div class="connection-address">
        <span class="connection-address-value">http://127.0.0.1:18789</span>
      </div>
      <label for="gateway-token">{{ $t("chat.gateway.token") }}</label>
      <div class="connection-token-field">
        <input
          id="gateway-token"
          v-model.trim="gatewayToken"
          :type="showGatewayToken ? 'text' : 'password'"
          spellcheck="false"
          autocomplete="off"
          :placeholder="$t('chat.gateway.tokenPlaceholder')"
          :disabled="status === 'connecting'"
          required
        />
        <button
          type="button"
          :title="
            $t(
              showGatewayToken
                ? 'chat.gateway.hideToken'
                : 'chat.gateway.showToken',
            )
          "
          :aria-label="
            $t(
              showGatewayToken
                ? 'chat.gateway.hideToken'
                : 'chat.gateway.showToken',
            )
          "
          @click="showGatewayToken = !showGatewayToken"
        >
          <EyeInvisibleOutlined v-if="showGatewayToken" />
          <EyeOutlined v-else />
        </button>
      </div>
      <p v-if="error" class="connection-error" role="alert">{{ error }}</p>
      <button
        type="submit"
        class="connection-submit"
        :disabled="status === 'connecting'"
      >
        <LoadingOutlined v-if="status === 'connecting'" />
        <ApiOutlined v-else />
        {{
          $t(
            status === "connecting"
              ? "chat.gateway.connecting"
              : "chat.gateway.connect",
          )
        }}
      </button>
      <button
        v-if="status === 'connected'"
        type="button"
        class="connection-cancel"
        @click="emit('back')"
      >
        {{ $t("chat.gateway.back") }}
      </button>
    </form>
    <div class="connection-footnote">{{ $t("chat.gateway.storageNote") }}</div>
  </div>
</template>

<script setup lang="ts">
import {
  ApiOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  LoadingOutlined,
} from "@ant-design/icons-vue";
import { ref } from "vue";
import type { ConnectionStatus } from "./WebSocketChatService";

const gatewayToken = defineModel<string>("gatewayToken", { required: true });
defineProps<{ status: ConnectionStatus; error: string }>();
const emit = defineEmits<{ connect: []; back: [] }>();
const showGatewayToken = ref(false);
</script>

<style scoped lang="less">
.connection-screen {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px 24px;
  background:
    radial-gradient(
      circle at 50% 10%,
      var(--color-primarySoft),
      transparent 58%
    ),
    var(--surface-panel-bg);
}

.connection-intro,
.connection-form,
.connection-footnote {
  width: min(100%, 440px);
}

.connection-intro {
  .connection-heading {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 10px;
  }

  .connection-heading-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: 6px;
  }

  .connection-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 52px;
    width: 52px;
    height: 52px;
    border-radius: 12px;
    background: var(--color-primaryBg);
    color: var(--color-primary);
    font-size: 24px;
  }

  .connection-eyebrow {
    color: var(--color-primary);
    font-size: var(--font-size-12);
    font-weight: 700;
  }

  h1 {
    margin: 0;
    color: var(--font-main-color);
    font-size: 28px;
    line-height: 1.25;
  }

  p {
    margin: 0 0 32px;
    color: var(--font-tip-color);
    line-height: 1.6;
  }
}

.connection-form {
  display: flex;
  flex-direction: column;
  gap: 10px;

  .connection-address {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    color: var(--font-tip-color);
    font-size: var(--font-size-13);
  }

  .connection-address-value {
    color: var(--font-main-color);
    font-weight: 600;
  }

  label {
    margin-top: 8px;
    color: var(--font-main-color);
    font-size: var(--font-size-13);
    font-weight: 600;
  }

  input {
    width: 100%;
    min-width: 0;
    height: 46px;
    padding: 0 14px;
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    outline: none;
    background: var(--bg-card-color);
    color: var(--font-main-color);

    &:focus {
      border-color: var(--color-primary);
      box-shadow: 0 0 0 3px var(--color-primaryBg);
    }
  }

  .connection-token-field {
    display: flex;
    min-width: 0;
    align-items: center;
    border: 1px solid var(--border-primary);
    border-radius: 8px;
    background: var(--bg-card-color);

    &:focus-within {
      border-color: var(--color-primary);
      box-shadow: 0 0 0 3px var(--color-primaryBg);
    }

    input {
      border: 0;
      box-shadow: none;
    }

    button {
      flex: 0 0 44px;
      height: 44px;
      border: 0;
      background: transparent;
      color: var(--font-tip-color);
      cursor: pointer;
    }
  }

  .connection-error {
    margin: 4px 0 0;
    color: var(--color-error);
    font-size: var(--font-size-13);
  }

  .connection-submit {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    min-height: 46px;
    margin-top: 18px;
    border: 0;
    border-radius: 8px;
    background: var(--color-primary);
    color: var(--color-white);
    font-weight: 600;
    cursor: pointer;

    &:hover:not(:disabled) {
      background: var(--color-primary-hover);
    }

    &:disabled {
      opacity: 0.65;
      cursor: wait;
    }
  }

  .connection-cancel {
    align-self: center;
    padding: 8px;
    border: 0;
    background: transparent;
    color: var(--color-primary);
    cursor: pointer;
  }
}

.connection-footnote {
  margin-top: 24px;
  color: var(--font-tip-color);
  font-size: var(--font-size-12);
  line-height: 1.5;
}
</style>
