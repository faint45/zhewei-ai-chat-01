# -*- coding: utf-8 -*-
"""
築未科技 — Yahoo Finance MCP Server（免費，無需 API Key）
─────────────────────────────────────────────────────────
提供股票報價、歷史數據、財報、新聞等功能。
適用角色：投資顧問分析師、大趨勢預測分析師、金融顧問、企業老闆
"""
import json
import sys
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    print("請安裝 yfinance: pip install yfinance", file=sys.stderr)
    sys.exit(1)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("yahoo-finance-mcp")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="stock_quote",
            description="取得股票即時報價（價格、漲跌幅、成交量、市值）",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代碼，如 AAPL, 2330.TW, TSLA"}
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="stock_history",
            description="取得股票歷史價格（OHLCV），支援 1d/5d/1mo/3mo/6mo/1y/5y",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代碼"},
                    "period": {"type": "string", "description": "期間：1d/5d/1mo/3mo/6mo/1y/5y", "default": "1mo"},
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="stock_financials",
            description="取得公司財報摘要（營收、EPS、本益比、殖利率等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代碼"}
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="stock_news",
            description="取得股票相關新聞（最近 10 則）",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代碼"}
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="market_overview",
            description="取得主要市場指數概覽（台股加權、S&P500、道瓊、那斯達克、比特幣）",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="compare_stocks",
            description="比較多檔股票的關鍵指標",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {"type": "string", "description": "逗號分隔的股票代碼，如 AAPL,MSFT,GOOGL"}
                },
                "required": ["symbols"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "stock_quote":
            return await _stock_quote(arguments["symbol"])
        elif name == "stock_history":
            return await _stock_history(arguments["symbol"], arguments.get("period", "1mo"))
        elif name == "stock_financials":
            return await _stock_financials(arguments["symbol"])
        elif name == "stock_news":
            return await _stock_news(arguments["symbol"])
        elif name == "market_overview":
            return await _market_overview()
        elif name == "compare_stocks":
            return await _compare_stocks(arguments["symbols"])
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"錯誤: {e}")]


async def _stock_quote(symbol: str):
    t = yf.Ticker(symbol)
    info = t.info
    data = {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName", ""),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "change": info.get("regularMarketChange"),
        "change_pct": info.get("regularMarketChangePercent"),
        "volume": info.get("regularMarketVolume"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "currency": info.get("currency", ""),
    }
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


async def _stock_history(symbol: str, period: str):
    t = yf.Ticker(symbol)
    df = t.history(period=period)
    if df.empty:
        return [TextContent(type="text", text=f"{symbol} 無歷史數據")]
    rows = []
    for idx, row in df.tail(20).iterrows():
        rows.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": round(row["Open"], 2),
            "high": round(row["High"], 2),
            "low": round(row["Low"], 2),
            "close": round(row["Close"], 2),
            "volume": int(row["Volume"]),
        })
    return [TextContent(type="text", text=json.dumps({"symbol": symbol, "period": period, "data": rows}, ensure_ascii=False, indent=2))]


async def _stock_financials(symbol: str):
    t = yf.Ticker(symbol)
    info = t.info
    data = {
        "symbol": symbol,
        "name": info.get("longName", ""),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "revenue": info.get("totalRevenue"),
        "profit_margin": info.get("profitMargins"),
        "roe": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "recommendation": info.get("recommendationKey", ""),
    }
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


async def _stock_news(symbol: str):
    t = yf.Ticker(symbol)
    news = t.news or []
    items = []
    for n in news[:10]:
        items.append({
            "title": n.get("title", ""),
            "publisher": n.get("publisher", ""),
            "link": n.get("link", ""),
            "published": n.get("providerPublishTime", ""),
        })
    return [TextContent(type="text", text=json.dumps({"symbol": symbol, "news": items}, ensure_ascii=False, indent=2))]


async def _market_overview():
    indices = {
        "^TWII": "台股加權指數",
        "^GSPC": "S&P 500",
        "^DJI": "道瓊工業",
        "^IXIC": "那斯達克",
        "BTC-USD": "比特幣",
    }
    results = []
    for sym, name in indices.items():
        try:
            t = yf.Ticker(sym)
            info = t.info
            results.append({
                "symbol": sym,
                "name": name,
                "price": info.get("regularMarketPrice"),
                "change_pct": info.get("regularMarketChangePercent"),
            })
        except Exception:
            results.append({"symbol": sym, "name": name, "price": None, "error": "取得失敗"})
    return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]


async def _compare_stocks(symbols_str: str):
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    results = []
    for sym in symbols[:10]:
        try:
            t = yf.Ticker(sym)
            info = t.info
            results.append({
                "symbol": sym,
                "name": info.get("longName", ""),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "pe": info.get("trailingPE"),
                "market_cap": info.get("marketCap"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
            })
        except Exception:
            results.append({"symbol": sym, "error": "取得失敗"})
    return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
