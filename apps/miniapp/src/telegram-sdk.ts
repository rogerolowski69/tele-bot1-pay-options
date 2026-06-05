import {
  init,
  initData,
  invoice,
  miniApp,
  openLink,
  retrieveRawInitData,
  viewport,
} from "@telegram-apps/sdk";

let sdkReady = false;

/** Initialize Telegram Mini Apps SDK (@telegram-apps/sdk / reactjs-template pattern). */
export function initTelegramSdk(): void {
  if (sdkReady) {
    return;
  }

  init();

  if (miniApp.mountSync.isAvailable()) {
    miniApp.mountSync();
  }

  if (miniApp.ready.isAvailable()) {
    miniApp.ready();
  }

  if (viewport.expand.isAvailable()) {
    viewport.expand();
  }

  try {
    initData.restore();
  } catch {
    // Running outside Telegram (local browser dev).
  }

  sdkReady = true;
}

export function getInitDataRaw(): string {
  const raw = initData.raw();
  if (raw) {
    return raw;
  }

  try {
    return retrieveRawInitData();
  } catch {
    return window.Telegram?.WebApp?.initData ?? "";
  }
}

export async function openTelegramInvoice(
  url: string,
  onPaid: () => void,
  onFailed: () => void,
): Promise<void> {
  if (invoice.open.isAvailable()) {
    const status = await invoice.open(url, "url");
    if (status === "paid") {
      onPaid();
      return;
    }
    if (status === "failed" || status === "cancelled") {
      onFailed();
    }
    return;
  }

  window.Telegram?.WebApp?.openInvoice(url, (status) => {
    if (status === "paid") {
      onPaid();
    }
    if (status === "failed" || status === "cancelled") {
      onFailed();
    }
  });
}

export function openExternalLink(url: string): void {
  if (openLink.isAvailable()) {
    openLink(url);
    return;
  }

  window.Telegram?.WebApp?.openLink(url);
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        openInvoice: (url: string, callback: (status: string) => void) => void;
        openLink: (url: string) => void;
      };
    };
  }
}

export {};
