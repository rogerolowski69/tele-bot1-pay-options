export type PaymentMethod = "stars" | "telegram_card" | "crypto" | "ton";

export interface PaymentConfig {
  stars: boolean;
  ton: boolean;
}

export interface Package {
  id: string;
  title: string;
  description: string;
  amount_minor: number;
  currency: string;
  is_digital: boolean;
}

interface CheckoutBase {
  order_id: string;
}

export interface TelegramInvoiceResponse extends CheckoutBase {
  type: "telegram_invoice";
  url: string;
}

export interface ExternalUrlResponse extends CheckoutBase {
  type: "external_url";
  url: string;
}

export interface TonCheckoutResponse extends CheckoutBase {
  type: "ton_payment";
  recipient: string;
  amount_nanoton: string;
  comment: string;
  network: "mainnet" | "testnet";
}

export type CheckoutResponse = TelegramInvoiceResponse | ExternalUrlResponse | TonCheckoutResponse;

export interface OrderDetail {
  order_id: string;
  status: string;
  package_id: string;
  package_title: string;
  payment_method: string;
  amount_minor: number;
  currency: string;
  delivery_message: string | null;
  status_message?: string | null;
  can_retry?: boolean;
  created_at?: string | null;
  can_resume_ton?: boolean;
}

export interface OrderSummary {
  order_id: string;
  status: string;
  package_id: string;
  package_title: string;
  payment_method: string;
  amount_minor: number;
  currency: string;
  status_message?: string | null;
  can_retry: boolean;
  created_at?: string | null;
  can_resume_ton: boolean;
}

export function isTonCheckout(data: CheckoutResponse): data is TonCheckoutResponse {
  return data.type === "ton_payment";
}

export function formatTonDisplay(nanoton: string | number): string {
  const value = Number(nanoton) / 1e9;
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 4 })} TON`;
}

export function formatPrice(amountMinor: number, currency: string): string {
  if (currency.toUpperCase() === "XTR") {
    return `⭐ ${amountMinor.toLocaleString()} Stars`;
  }
  if (currency.toUpperCase() === "TON") {
    return formatTonDisplay(amountMinor);
  }
  return `${amountMinor} ${currency}`;
}

export function formatOrderStatus(status: string): string {
  const labels: Record<string, string> = {
    pending: "Pending",
    invoice_created: "Awaiting payment",
    paid: "Paid",
    failed: "Failed",
    expired: "Expired",
    cancelled: "Cancelled",
    refunded: "Refunded",
  };
  return labels[status] ?? status;
}
