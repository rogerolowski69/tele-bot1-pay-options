import type { CheckoutResponse, PaymentMethod } from "./types";
import { getInitDataRaw, openExternalLink, openTelegramInvoice } from "./telegram-sdk";

export async function fetchPackages() {
  const res = await fetch("/api/packages");
  if (!res.ok) {
    throw new Error("Failed to load packages");
  }
  return res.json();
}

export async function checkout(packageId: string, method: PaymentMethod): Promise<CheckoutResponse> {
  const res = await fetch("/api/checkout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitDataRaw(),
    },
    body: JSON.stringify({
      package_id: packageId,
      method,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Checkout failed");
  }

  return res.json();
}

export function openPayment(data: CheckoutResponse, onPaid: () => void, onFailed: () => void): void {
  if (data.type === "telegram_invoice") {
    void openTelegramInvoice(data.url, onPaid, onFailed);
    return;
  }

  if (data.type === "external_url") {
    openExternalLink(data.url);
  }
}
