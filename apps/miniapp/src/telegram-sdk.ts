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

const INVOICE_TIMEOUT_MS = 600_000;

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

function invoiceErrorMessage(status: string): string {
  if (status === "cancelled") {
    return "Payment cancelled";
  }
  if (status === "failed") {
    return "Payment failed";
  }
  return "Payment was not completed";
}

/** Open a Telegram Stars invoice and resolve when paid or reject on any other outcome. */
export function openTelegramInvoice(url: string): Promise<void> {
  if (invoice.open.isAvailable()) {
    return invoice.open(url, "url").then((status) => {
      if (status === "paid") {
        return;
      }
      throw new Error(invoiceErrorMessage(status));
    });
  }

  return new Promise((resolve, reject) => {
    const webApp = window.Telegram?.WebApp;
    if (!webApp?.openInvoice) {
      reject(new Error("Telegram invoice API is not available"));
      return;
    }

    let settled = false;
    const timeout = window.setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      reject(new Error("Payment cancelled"));
    }, INVOICE_TIMEOUT_MS);

    webApp.openInvoice(url, (status) => {
      if (settled) {
        return;
      }
      settled = true;
      window.clearTimeout(timeout);

      if (status === "paid") {
        resolve();
        return;
      }
      reject(new Error(invoiceErrorMessage(status)));
    });
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
