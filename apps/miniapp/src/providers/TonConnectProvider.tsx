import type { PropsWithChildren } from "react";
import { TonConnectUIProvider } from "@tonconnect/ui-react";

function manifestUrl(): string {
  const origin =
    import.meta.env.VITE_MINIAPP_ORIGIN ||
    (typeof window !== "undefined" ? window.location.origin : "http://localhost:5173");
  return `${origin}/tonconnect-manifest.json`;
}

export function TonConnectProvider({ children }: PropsWithChildren) {
  return (
    <TonConnectUIProvider manifestUrl={manifestUrl()} uiPreferences={{ theme: "DARK" }}>
      {children}
    </TonConnectUIProvider>
  );
}
