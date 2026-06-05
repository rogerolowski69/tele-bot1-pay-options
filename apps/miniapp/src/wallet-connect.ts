import type { TonConnectUI } from "@tonconnect/ui-react";

const DEFAULT_TIMEOUT_MS = 120_000;

/** Wait for TonConnect wallet after opening the modal (avoids connected-state race). */
export async function ensureTonWalletConnected(
  tonConnectUI: TonConnectUI,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<void> {
  if (tonConnectUI.connected) {
    return;
  }

  await tonConnectUI.openModal();

  if (tonConnectUI.connected) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      unsubscribe();
      reject(new Error("Wallet not connected"));
    }, timeoutMs);

    const unsubscribe = tonConnectUI.onStatusChange((wallet) => {
      if (!wallet) {
        return;
      }
      window.clearTimeout(timeout);
      unsubscribe();
      resolve();
    });

    if (tonConnectUI.connected) {
      window.clearTimeout(timeout);
      unsubscribe();
      resolve();
    }
  });
}
