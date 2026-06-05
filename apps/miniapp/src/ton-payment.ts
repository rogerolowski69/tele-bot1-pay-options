import { beginCell } from "@ton/core";
import { CHAIN, type TonConnectUI } from "@tonconnect/ui-react";

import type { TonCheckoutResponse } from "./types";

const CONFIRM_POLL_MS = 2500;
const CONFIRM_MAX_ATTEMPTS = 24;

function tonChain(network: string): CHAIN {
  return network === "mainnet" ? CHAIN.MAINNET : CHAIN.TESTNET;
}

function commentPayload(comment: string): string {
  return beginCell().storeUint(0, 32).storeStringTail(comment).endCell().toBoc().toString("base64");
}

export async function sendTonPayment(
  tonConnectUI: TonConnectUI,
  payment: TonCheckoutResponse,
): Promise<void> {
  await tonConnectUI.sendTransaction({
    validUntil: Math.floor(Date.now() / 1000) + 600,
    network: tonChain(payment.network),
    messages: [
      {
        address: payment.recipient,
        amount: payment.amount_nanoton,
        payload: commentPayload(payment.comment),
      },
    ],
  });
}

export async function confirmTonPayment(orderId: string): Promise<{ status: string; tx_hash?: string }> {
  const { getInitDataRaw } = await import("./telegram-sdk");
  const res = await fetch("/api/checkout/ton/confirm", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitDataRaw(),
    },
    body: JSON.stringify({ order_id: orderId }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message = err.error?.message || err.detail || "TON confirmation failed";
    throw new Error(message);
  }

  return res.json();
}

export async function pollTonConfirmation(orderId: string): Promise<{ status: string; tx_hash?: string }> {
  for (let attempt = 0; attempt < CONFIRM_MAX_ATTEMPTS; attempt += 1) {
    const result = await confirmTonPayment(orderId);
    if (result.status === "paid") {
      return result;
    }
    await new Promise((resolve) => setTimeout(resolve, CONFIRM_POLL_MS));
  }
  throw new Error("Payment not confirmed on-chain yet. Try again in a minute.");
}
