import yfinance as yf
import pandas as pd
from datetime import datetime
from database import get_connection

def save_asset_and_prices(ticker: str, asset_name: str = None, asset_type: str = "EQUITY", start_date: str = "2020-01-01"):
    """
    Yahoo Finance uzerinden hisse verisini ceker;
    'assets' ve 'daily_prices' tablolarina kaydeder/gunceller.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if asset_name is None:
        asset_name = ticker

    # 1. Assets tablosuna hisseyi ekle veya varsa gec
    cursor.execute("""
    INSERT OR IGNORE INTO assets (ticker, asset_name, asset_type)
    VALUES (?, ?, ?)
    """, (ticker, asset_name, asset_type))
    conn.commit()

    # Varligin asset_id degerini al
    cursor.execute("SELECT asset_id FROM assets WHERE ticker = ?", (ticker,))
    asset_id = cursor.fetchone()[0]

    # 2. Yahoo Finance'den fiyatlari cek
    print(f"[{ticker}] verisi indiriliyor...")
    data = yf.download(ticker, start=start_date, progress=False)

    if data.empty:
        print(f"Uyari: {ticker} icin veri bulunamadi.")
        conn.close()
        return

    # Eger coklu indeks gelirse duzlestir
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    # 'Adj Close' varsa onu, yoksa 'Close' sutununu al
    price_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'

    # 3. daily_prices tablosuna ekle
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
    print(f"[{ticker}] basariyla kaydedildi: Toplam {len(records)} gunluk fiyat eklendi.")

def seed_default_assets():
    """BIST ve kuresel ornek hisseleri veritabanina yukler."""
    sample_assets = [
        {"ticker": "THYAO.IS", "name": "Turk Hava Yollari", "type": "EQUITY"},
        {"ticker": "GARAN.IS", "name": "Garanti Bankasi", "type": "EQUITY"},
        {"ticker": "ASELS.IS", "name": "Aselsan", "type": "EQUITY"},
        {"ticker": "EREGL.IS", "name": "Eregli Demir Celik", "type": "EQUITY"},
        {"ticker": "AAPL",     "name": "Apple Inc.", "type": "EQUITY"}
    ]

    for item in sample_assets:
        save_asset_and_prices(
            ticker=item["ticker"],
            asset_name=item["name"],
            asset_type=item["type"],
            start_date="2021-01-01"
        )

if __name__ == "__main__":
    seed_default_assets()
