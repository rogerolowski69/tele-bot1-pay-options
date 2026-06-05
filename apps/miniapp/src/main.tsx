import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import { AppRoot } from "@telegram-apps/telegram-ui";
import "@telegram-apps/telegram-ui/dist/styles.css";

import { checkout, fetchPackages, openPayment } from "./api";
import { initTelegramSdk } from "./telegram-sdk";
import type { Package, PaymentMethod } from "./types";

function ShopPage() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchPackages().then(setPackages).catch(() => setError("Could not load packages"));
  }, []);

  async function handlePay(pkg: Package, method: PaymentMethod) {
    setLoading(`${pkg.id}:${method}`);
    setError(null);
    try {
      const data = await checkout(pkg.id, method);
      openPayment(
        data,
        () => navigate("/success"),
        () => navigate("/checkout?failed=1"),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main style={{ padding: 16 }}>
      <h1>Choose a package</h1>
      {error && <p style={{ color: "var(--tg-theme-destructive-text-color, red)" }}>{error}</p>}
      {packages.map((pkg) => (
        <section key={pkg.id} style={{ marginBottom: 24, padding: 16, borderRadius: 12, background: "var(--tg-theme-secondary-bg-color)" }}>
          <h2>{pkg.title}</h2>
          <p>{pkg.description}</p>
          <p>
            {pkg.amount_minor} {pkg.currency}
            {pkg.is_digital ? " (digital)" : ""}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {pkg.is_digital && (
              <button disabled={!!loading} onClick={() => handlePay(pkg, "stars")}>
                {loading === `${pkg.id}:stars` ? "…" : "Pay with Stars ⭐"}
              </button>
            )}
            {!pkg.is_digital && (
              <button disabled={!!loading} onClick={() => handlePay(pkg, "telegram_card")}>
                {loading === `${pkg.id}:telegram_card` ? "…" : "Pay with Card 💳"}
              </button>
            )}
            {!pkg.is_digital && (
              <button disabled={!!loading} onClick={() => handlePay(pkg, "crypto")}>
                {loading === `${pkg.id}:crypto` ? "…" : "Pay with Crypto ₿"}
              </button>
            )}
          </div>
        </section>
      ))}
    </main>
  );
}

function CheckoutPage() {
  const [params] = useSearchParams();
  const failed = params.get("failed");

  return (
    <main style={{ padding: 16 }}>
      <h1>Checkout</h1>
      {failed ? <p>Payment was cancelled or failed. Try again from the shop.</p> : <p>Select a package to continue.</p>}
    </main>
  );
}

function SuccessPage() {
  return (
    <main style={{ padding: 16 }}>
      <h1>Payment successful</h1>
      <p>Your order is being processed. Delivery happens after backend confirmation.</p>
    </main>
  );
}

function App() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    initTelegramSdk();
    setReady(true);
  }, []);

  if (!ready) {
    return null;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ShopPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/success" element={<SuccessPage />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppRoot>
      <App />
    </AppRoot>
  </StrictMode>,
);
