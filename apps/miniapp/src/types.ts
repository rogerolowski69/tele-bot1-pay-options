export type PaymentMethod = "stars" | "telegram_card" | "crypto";

export interface Package {
  id: string;
  title: string;
  description: string;
  amount_minor: number;
  currency: string;
  is_digital: boolean;
}

export interface CheckoutResponse {
  type: "telegram_invoice" | "external_url";
  url: string;
  order_id: string;
}
