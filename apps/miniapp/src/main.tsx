import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import { AppRoot } from "@telegram-apps/telegram-ui";
import "@telegram-apps/telegram-ui/dist/styles.css";
import { TonConnectButton, useTonConnectUI } from "@tonconnect/ui-react";

import {
  checkout,
  fetchMyOrders,
  fetchOrder,
  fetchPackages,
  fetchPaymentConfig,
  fetchTonPaymentResume,
  payWithStars,
  payWithTon,
  checkTonPayment,
} from "./api";
import { TonConnectProvider } from "./providers/TonConnectProvider";
import { initTelegramSdk } from "./telegram-sdk";
import type { OrderSummary, Package, PaymentConfig, PaymentMethod, TonCheckoutResponse } from "./types";
import { formatOrderStatus, formatPrice } from "./types";

function AppHeader({ title, showWallet }: { title: string; showWallet?: boolean }) {
  return (
    <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
      <h1 style={{ margin: 0, fontSize: "1.25rem" }}>{title}</h1>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <Link to="/orders" style={{ fontSize: "0.875rem" }}>
          My purchases
        </Link>
        {showWallet && <TonConnectButton />}
      </div>
    </header>
  );
}

function packagePayOptions(pkg: Package, config: PaymentConfig): PaymentMethod[] {
  const methods: PaymentMethod[] = [];
  if (pkg.is_digital && config.stars) {
    methods.push("stars");
  }
  if (!pkg.is_digital && config.ton) {
    methods.push("ton");
  }
  return methods;
}

function ShopPage() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [paymentConfig, setPaymentConfig] = useState<PaymentConfig>({ stars: true, ton: false });
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([fetchPackages(), fetchPaymentConfig()])
      .then(([pkgs, config]) => {
        setPackages(pkgs);
        setPaymentConfig(config);
      })
      .catch(() => setError("Could not load shop"));
  }, []);

  async function handlePay(pkg: Package, method: PaymentMethod) {
    setLoading(`${pkg.id}:${method}`);
    setError(null);
    try {
      const data = await checkout(pkg.id, method);

      if (method === "stars") {
        const order = await payWithStars(data, data.order_id);
        navigate(`/success?order_id=${order.order_id}`);
        return;
      }

      if (method === "ton") {
        navigate(`/checkout/ton?order_id=${data.order_id}`);
        return;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main style={{ padding: 16 }}>
      <AppHeader title="Shop" showWallet={paymentConfig.ton} />
      {error && <p style={{ color: "var(--tg-theme-destructive-text-color, red)" }}>{error}</p>}
      {packages.map((pkg) => {
        const methods = packagePayOptions(pkg, paymentConfig);
        return (
          <section
            key={pkg.id}
            style={{
              marginBottom: 24,
              padding: 16,
              borderRadius: 12,
              background: "var(--tg-theme-secondary-bg-color)",
            }}
          >
            <h2>{pkg.title}</h2>
            <p>{pkg.description}</p>
            <p>{formatPrice(pkg.amount_minor, pkg.currency)}{pkg.is_digital ? " · digital" : ""}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {methods.includes("stars") && (
                <button disabled={!!loading} onClick={() => handlePay(pkg, "stars")}>
                  {loading === `${pkg.id}:stars` ? "…" : "Pay with Stars ⭐"}
                </button>
              )}
              {methods.includes("ton") && (
                <button disabled={!!loading} onClick={() => handlePay(pkg, "ton")}>
                  {loading === `${pkg.id}:ton` ? "…" : "Pay with TON 💎"}
                </button>
              )}
              {methods.length === 0 && (
                <p style={{ opacity: 0.7, margin: 0 }}>
                  {pkg.is_digital
                    ? "Stars payments only work inside Telegram."
                    : "TON payments are not configured yet."}
                </p>
              )}
            </div>
          </section>
        );
      })}
    </main>
  );
}

function OrdersPage() {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchMyOrders()
      .then(setOrders)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load orders"));
  }, []);

  function handleSelect(order: OrderSummary) {
    if (order.status === "paid") {
      navigate(`/success?order_id=${order.order_id}`);
      return;
    }
    if (order.can_resume_ton) {
      navigate(`/checkout/ton?order_id=${order.order_id}`);
    }
  }

  return (
    <main style={{ padding: 16 }}>
      <AppHeader title="My purchases" />
      <p style={{ marginTop: 0 }}>
        <Link to="/">← Back to shop</Link>
      </p>
      {error && <p style={{ color: "var(--tg-theme-destructive-text-color, red)" }}>{error}</p>}
      {orders.length === 0 && !error && <p>No purchases yet.</p>}
      {orders.map((order) => (
        <section
          key={order.order_id}
          style={{
            marginBottom: 16,
            padding: 16,
            borderRadius: 12,
            background: "var(--tg-theme-secondary-bg-color)",
            cursor: order.status === "paid" || order.can_resume_ton ? "pointer" : "default",
          }}
          onClick={() => handleSelect(order)}
        >
          <strong>{order.package_title}</strong>
          <p style={{ margin: "4px 0" }}>{formatPrice(order.amount_minor, order.currency)}</p>
          <p style={{ margin: "4px 0", opacity: 0.85 }}>{formatOrderStatus(order.status)}</p>
          {order.status_message && (
            <p style={{ margin: "8px 0 0", opacity: 0.9 }}>{order.status_message}</p>
          )}
          {order.can_retry && (
            <p style={{ margin: "8px 0 0" }}>
              <Link to="/" onClick={(event) => event.stopPropagation()}>
                Purchase again from shop →
              </Link>
            </p>
          )}
          {order.can_resume_ton && (
            <p style={{ margin: "8px 0 0", color: "var(--tg-theme-link-color, #2481cc)" }}>
              Tap to resume TON payment →
            </p>
          )}
        </section>
      ))}
    </main>
  );
}

function TonCheckoutPage() {
  const [params] = useSearchParams();
  const orderId = params.get("order_id") ?? "";
  const [checkoutData, setCheckoutData] = useState<TonCheckoutResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "idle" | "sending" | "confirming" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [amountLabel, setAmountLabel] = useState<string>("");
  const [tonConnectUI] = useTonConnectUI();
  const navigate = useNavigate();

  useEffect(() => {
    if (!orderId) {
      setError("Missing order");
      setStatus("error");
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const order = await fetchOrder(orderId);
        if (cancelled) {
          return;
        }
        if (order.status === "paid") {
          navigate(`/success?order_id=${orderId}`);
          return;
        }
        if (order.status === "expired" || order.status === "failed") {
          setError(order.status_message ?? "This order cannot be resumed. Start a new checkout from the shop.");
          setStatus("error");
          return;
        }
        setAmountLabel(formatPrice(order.amount_minor, order.currency));
        const tonPayment = await fetchTonPaymentResume(orderId);
        if (!cancelled) {
          setCheckoutData(tonPayment);
          setStatus("idle");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not load order");
          setStatus("error");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [orderId, navigate]);

  async function handleSendTon() {
    if (!checkoutData) {
      return;
    }
    setStatus("sending");
    setError(null);
    try {
      setStatus("confirming");
      const order = await payWithTon(checkoutData, tonConnectUI);
      navigate(`/success?order_id=${order.order_id}`);
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "TON payment failed");
    }
  }

  async function handleCheckPayment() {
    if (!orderId) {
      return;
    }
    setError(null);
    try {
      const order = await checkTonPayment(orderId);
      navigate(`/success?order_id=${order.order_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not check payment");
    }
  }

  return (
    <main style={{ padding: 16 }}>
      <AppHeader title="Pay with TON" showWallet />
      <p style={{ marginTop: 0 }}>
        <Link to="/orders">My purchases</Link>
      </p>
      {amountLabel && <p>Amount: {amountLabel}</p>}
      <p>Connect your wallet and send the transaction. Delivery goes to your Telegram chat once confirmed.</p>
      {status === "confirming" && <p>Confirming on-chain payment…</p>}
      {error && <p style={{ color: "var(--tg-theme-destructive-text-color, red)" }}>{error}</p>}
      {status === "error" && (
        <p>
          <Link to="/">← Back to shop</Link>
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          disabled={status !== "idle" && status !== "error" || !checkoutData}
          onClick={handleSendTon}
        >
          {status === "sending" ? "Opening wallet…" : status === "confirming" ? "Confirming…" : "Send TON payment"}
        </button>
        <button type="button" onClick={handleCheckPayment} disabled={!orderId}>
          I already paid — check status
        </button>
      </div>
    </main>
  );
}

function SuccessPage() {
  const [params] = useSearchParams();
  const orderId = params.get("order_id") ?? "";
  const [delivery, setDelivery] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      return;
    }
    fetchOrder(orderId)
      .then((order) => {
        setTitle(order.package_title);
        setDelivery(order.delivery_message);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load order"));
  }, [orderId]);

  return (
    <main style={{ padding: 16 }}>
      <h1>Payment successful</h1>
      {title && <h2>{title}</h2>}
      {delivery ? (
        <p style={{ whiteSpace: "pre-wrap" }}>{delivery}</p>
      ) : (
        <p>Your order is confirmed. Check your Telegram chat for delivery details.</p>
      )}
      {error && <p style={{ color: "var(--tg-theme-destructive-text-color, red)" }}>{error}</p>}
      <p style={{ marginTop: 24 }}>
        <Link to="/orders">View all purchases</Link>
        {" · "}
        <Link to="/">Back to shop</Link>
      </p>
    </main>
  );
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ShopPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/checkout/ton" element={<TonCheckoutPage />} />
        <Route path="/success" element={<SuccessPage />} />
      </Routes>
    </BrowserRouter>
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
    <TonConnectProvider>
      <AppRoutes />
    </TonConnectProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppRoot>
      <App />
    </AppRoot>
  </StrictMode>,
);
