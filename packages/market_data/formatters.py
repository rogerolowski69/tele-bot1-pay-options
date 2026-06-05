from typing import Any


def _fmt_money(value: Any) -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
        if abs(num) >= 1_000_000_000:
            return f"${num / 1_000_000_000:.2f}B"
        if abs(num) >= 1_000_000:
            return f"${num / 1_000_000:.2f}M"
        return f"${num:,.2f}"
    except (TypeError, ValueError):
        return str(value)


def format_crypto(data: dict[str, Any]) -> str:
    name = data.get("name", data.get("id", "?"))
    sym = str(data.get("symbol", "")).upper()
    price = data.get("price")
    chg = data.get("change_24h_pct")
    mcap = data.get("market_cap")
    vol = data.get("volume_24h")
    cached = " (cached)" if data.get("cached") else ""
    lines = [
        f"🪙 *{name}* ({sym}){cached}",
        f"Price: `{price}` USD",
    ]
    if chg is not None:
        lines.append(f"24h: `{chg:+.2f}%`")
    if mcap:
        lines.append(f"Market cap: `{_fmt_money(mcap)}`")
    if vol:
        lines.append(f"24h volume: `{_fmt_money(vol)}`")
    return "\n".join(lines)


def format_stock(data: dict[str, Any]) -> str:
    sym = data.get("symbol", "?")
    price = data.get("price")
    cached = " (cached)" if data.get("cached") else ""
    lines = [f"📈 *{sym}*{cached}", f"Price: `{price}`"]
    if data.get("market_cap"):
        lines.append(f"Market cap: `{_fmt_money(data['market_cap'])}`")
    if data.get("volume"):
        lines.append(f"Volume: `{data['volume']:,}`")
    if data.get("source"):
        lines.append(f"_Source: {data['source']}_")
    return "\n".join(lines)


def format_options(data: dict[str, Any]) -> str:
    sym = data.get("symbol", "?")
    exp = data.get("nearest_expiration", "—")
    cached = " (cached)" if data.get("cached") else ""
    lines = [
        f"📊 *Options — {sym}*{cached}",
        f"Nearest expiry: `{exp}` ({data.get('expirations_count', 0)} total)",
        "",
        "*Top calls*",
    ]
    for c in data.get("calls", [])[:3]:
        lines.append(
            f"  `{c['strike']}` last `{c['last']}` vol `{c['volume']}` OI `{c['open_interest']}`"
        )
    lines.append("")
    lines.append("*Top puts*")
    for p in data.get("puts", [])[:3]:
        lines.append(
            f"  `{p['strike']}` last `{p['last']}` vol `{p['volume']}` OI `{p['open_interest']}`"
        )
    return "\n".join(lines)


def format_fundamentals(data: dict[str, Any]) -> str:
    sym = data.get("symbol", "?")
    cached = " (cached)" if data.get("cached") else ""
    lines = [f"📋 *Fundamentals — {sym}*{cached}"]

    sec = data.get("sec")
    if sec:
        lines.append("")
        lines.append(f"*SEC EDGAR* — {sec.get('entity_name', sym)}")
        lines.append(f"CIK: `{sec.get('cik')}`")
        for label, key in [("Assets", "assets"), ("Revenue", "revenue"), ("Net income", "net_income")]:
            node = sec.get(key)
            if node:
                val = node.get("val")
                end = node.get("end", "")
                lines.append(f"{label}: `{_fmt_money(val)}` ({end})")
    elif data.get("sec_error"):
        lines.append(f"\nSEC: _{data['sec_error']}_")

    yf = data.get("yfinance")
    if yf:
        lines.append("")
        lines.append(f"*yfinance* — {yf.get('name', sym)}")
        if yf.get("sector"):
            lines.append(f"Sector: `{yf['sector']}`")
        if yf.get("pe_ratio"):
            lines.append(f"P/E: `{yf['pe_ratio']:.2f}`")
        if yf.get("total_assets"):
            lines.append(f"Total assets: `{_fmt_money(yf['total_assets'])}`")
        if yf.get("total_revenue"):
            lines.append(f"Revenue: `{_fmt_money(yf['total_revenue'])}`")

    return "\n".join(lines)
