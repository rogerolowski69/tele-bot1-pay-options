import type { CheckoutResponse, OrderDetail, OrderSummary, PaymentConfig, PaymentMethod, TonCheckoutResponse } from "./types";
import { isTonCheckout } from "./types";
import { getInitDataRaw, openTelegramInvoice } from "./telegram-sdk";
import { pollTonConfirmation, sendTonPayment, confirmTonPayment } from "./ton-payment";
import { ensureTonWalletConnected } from "./wallet-connect";
import type { TonConnectUI } from "@tonconnect/ui-react";

const POLL_MS = 2000;
const POLL_MAX = 30;

function parseApiError(err: Record<string, unknown>): string {
  const nested = err.error as { message?: string } | undefined;
  return nested?.message || (err.detail as string) || "Request failed";
}

function authHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-Telegram-Init-Data": getInitDataRaw(),
  };
}

function assertOrderPayable(order: OrderDetail): void {
  if (order.status === "failed") {
    throw new Error(order.status_message ?? "Payment failed. Try again from the shop.");
  }
  if (order.status === "expired") {
    throw new Error(order.status_message ?? "Order expired. Start a new checkout from the shop.");
  }
}

export async function fetchPaymentConfig(): Promise<PaymentConfig> {
  const res = await fetch("/api/config/payments");
  if (!res.ok) {
    return { stars: true, ton: false };
  }
  return res.json();
}

export async function fetchPackages() {
  const res = await fetch("/api/packages");
  if (!res.ok) {
    throw new Error("Failed to load packages");
  }
  return res.json();
}

export async function fetchMyOrders(): Promise<OrderSummary[]> {
  const res = await fetch("/api/orders/me", { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function fetchTonPaymentResume(orderId: string): Promise<TonCheckoutResponse> {
  const res = await fetch(`/api/orders/${orderId}/ton-payment`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  const data = await res.json();
  return { ...data, type: "ton_payment" as const };
}

export async function fetchOrder(orderId: string): Promise<OrderDetail> {
  const res = await fetch(`/api/orders/${orderId}`, { headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }
  return res.json();
}

export async function pollOrderPaid(orderId: string): Promise<OrderDetail> {
  for (let attempt = 0; attempt < POLL_MAX; attempt += 1) {
    const order = await fetchOrder(orderId);
    if (order.status === "paid") {
      return order;
    }
    if (order.status === "failed" || order.status === "expired") {
      assertOrderPayable(order);
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }
  throw new Error("Payment not confirmed yet. Check your Telegram chat for delivery.");
}

export async function checkout(packageId: string, method: PaymentMethod): Promise<CheckoutResponse> {
  const res = await fetch("/api/checkout", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      package_id: packageId,
      method,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(parseApiError(err));
  }

  return res.json();
}

export async function payWithStars(data: CheckoutResponse, orderId: string): Promise<OrderDetail> {
  if (data.type !== "telegram_invoice") {
    throw new Error("Expected Telegram invoice");
  }

  await openTelegramInvoice(data.url);
  return pollOrderPaid(orderId);
}

export async function payWithTon(
  data: CheckoutResponse,
  tonConnectUI: TonConnectUI,
): Promise<OrderDetail> {
  if (!isTonCheckout(data)) {
    throw new Error("Expected TON payment");
  }

  await ensureTonWalletConnected(tonConnectUI);

  await sendTonPayment(tonConnectUI, data);
  const confirmed = await pollTonConfirmation(data.order_id);
  if (confirmed.status !== "paid") {
    throw new Error("On-chain payment not confirmed yet");
  }
  return fetchOrder(data.order_id);
}

export async function checkTonPayment(orderId: string): Promise<OrderDetail> {
  const result = await confirmTonPayment(orderId);
  if (result.status !== "paid") {
    throw new Error("Payment not confirmed on-chain yet. Try again in a moment.");
  }
  return fetchOrder(orderId);
}
