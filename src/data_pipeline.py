import sys
import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# database modülüne erişim sağlamak için dizin ayarı
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_connection

def save_asset_and_prices(ticker: str, asset_name: str = None, asset_type: str = "EQUITY", start_date: str = "2021-01-01"):
    conn = get_connection()
    cursor = conn.cursor()

    if asset_name is None:
        asset_name = ticker

    cursor.execute("""
    INSERT OR IGNORE INTO assets (ticker, asset_name, asset_type)
    VALUES (?, ?, ?)
    """, (ticker, asset_name, asset_type))
    conn.commit()

    cursor.execute("SELECT asset_id FROM assets WHERE ticker = ?", (ticker,))
    asset_id = cursor.fetchone()[0]

    print(f"[{ticker}] verisi indiriliyor...")
    data = yf.download(ticker, start=start_date, progress=False)

    if data.empty:
        print(f"Uyari: {ticker} icin veri bulunamadi.")
        conn.close()
        return

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    price_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'

    records = []
    for date, row in data.iterrows():
        price_date = date.strftime('%Y-%m-%d')
        adj_close = float(row[price_col])
        if pd.notna(adj_close):
            records.append((asset_id, price_date, adj_close))

    cursor.executemany("""
    INSERT OR REPLACE INTO daily_prices (asset_id, price_date, adj_close)
    VALUES (?, ?, ?)
    """, records)

    conn.commit()
    conn.close()
    print(f"[{ticker}] basariyla kaydedildi.")

def seed_default_assets():
    sample_assets = [
        {"ticker": "THYAO.IS", "name": "Turk Hava Yollari", "type": "EQUITY"},
        {"ticker": "GARAN.IS", "name": "Garanti Bankasi", "type": "EQUITY"},
        {"ticker": "ASELS.IS", "name": "Aselsan", "type": "EQUITY"},
        {"ticker": "EREGL.IS", "name": "Eregli Demir Celik", "type": "EQUITY"}
    ]
    for item in sample_assets:
        save_asset_and_prices(item["ticker"], item["name"], item["type"], start_date="2021-01-01")

def create_or_update_portfolio(portfolio_name: str, total_capital: float, weights_dict: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT portfolio_id FROM portfolios WHERE portfolio_name = ?", (portfolio_name,))
    row = cursor.fetchone()
    if row:
        portfolio_id = row[0]
        cursor.execute("UPDATE portfolios SET total_capital = ? WHERE portfolio_id = ?", (total_capital, portfolio_id))
    else:
        cursor.execute("INSERT INTO portfolios (portfolio_name, total_capital) VALUES (?, ?)", (portfolio_name, total_capital))
        portfolio_id = cursor.lastrowid

    cursor.execute("DELETE FROM portfolio_weights WHERE portfolio_id = ?", (portfolio_id,))

    for ticker, weight in weights_dict.items():
        cursor.execute("SELECT asset_id FROM assets WHERE ticker = ?", (ticker,))
        asset_row = cursor.fetchone()
        if asset_row:
            asset_id = asset_row[0]
            cursor.execute("""
            INSERT INTO portfolio_weights (portfolio_id, asset_id, weight)
            VALUES (?, ?, ?)
            """, (portfolio_id, asset_id, weight))
        else:
            print(f"Hata: {ticker} veritabaninda bulunamadi!")

    conn.commit()
    conn.close()
    print(f"Portfoy [{portfolio_name}] (ID: {portfolio_id}) ve agirliklar basariyla kaydedildi.")
    return portfolio_id

def get_portfolio_returns(portfolio_id: int):
    conn = get_connection()

    query = """
    SELECT 
        a.ticker,
        pw.weight,
        dp.price_date,
        dp.adj_close
    FROM portfolio_weights pw
    JOIN assets a ON pw.asset_id = a.asset_id
    JOIN daily_prices dp ON a.asset_id = dp.asset_id
    WHERE pw.portfolio_id = ?
    ORDER BY dp.price_date ASC;
    """
    df = pd.read_sql_query(query, conn, params=(portfolio_id,))
    conn.close()

    if df.empty:
        raise ValueError(f"Portfoy ID {portfolio_id} icin fiyat verisi bulunamadi!")

    price_pivot = df.pivot(index='price_date', columns='ticker', values='adj_close')
    price_pivot = price_pivot.ffill().dropna()

    returns_df = np.log(price_pivot / price_pivot.shift(1)).dropna()
    weights_series = df[['ticker', 'weight']].drop_duplicates().set_index('ticker')['weight']

    return returns_df, weights_series

if __name__ == "__main__":
    sample_portfolio = {
        "THYAO.IS": 0.35,
        "GARAN.IS": 0.25,
        "ASELS.IS": 0.20,
        "EREGL.IS": 0.20
    }
    pid = create_or_update_portfolio("BIST_Dinamik_Portfoy", 1_000_000, sample_portfolio)

    returns, weights = get_portfolio_returns(pid)
    print("\n--- Getiri Matrisi Ilk 5 Gun ---")
    print(returns.head())
    print("\n--- Portfoy Agirliklari ---")
    print(weights)
