import sqlite3
import os

# Veritabanı dosyasının data/ klasörü altında market_data.db olarak kaydedileceği yol
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market_data.db")

def get_connection():
    """SQLite veritabanına bağlantı oluşturur ve Foreign Key kısıtlamalarını aktif eder."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Veritabanı tablolarını ve indeksleri oluşturur."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Assets (Varlık Tanımları) Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker VARCHAR(15) NOT NULL UNIQUE,
        asset_name VARCHAR(100),
        asset_type VARCHAR(20) DEFAULT 'EQUITY',
        currency VARCHAR(3) DEFAULT 'TRY'
    );
    """)

    # 2. Portfolios (Portföy Bilgisi) Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
        portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_name VARCHAR(50) NOT NULL,
        total_capital REAL NOT NULL,
        created_at DATE DEFAULT CURRENT_DATE
    );
    """)

    # 3. Portfolio Weights (Portföy Ağırlıkları) Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_weights (
        portfolio_id INTEGER,
        asset_id INTEGER,
        weight REAL NOT NULL,
        PRIMARY KEY (portfolio_id, asset_id),
        FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
        FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
    );
    """)

    # 4. Daily Prices (Zaman Serisi Fiyatlar) Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_prices (
        price_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        price_date DATE NOT NULL,
        adj_close REAL NOT NULL,
        FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
        UNIQUE(asset_id, price_date)
    );
    """)

    # Performans için Hızlı Arama İndeksi
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_prices_asset_date 
    ON daily_prices(asset_id, price_date);
    """)

    conn.commit()
    conn.close()
    print("Veritabani tablolari ve indeksler basariyla olusturuldu.")

if __name__ == "__main__":
    init_db()
