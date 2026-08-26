import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market_data.db")

def get_connection():
    """SQLite veritabanına bağlantı oluşturur ve Foreign Key kısıtlamalarını aktif eder."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Tabloları, indeksleri ve analitik SQL görünümlerini (VIEW) oluşturur."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Assets Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker VARCHAR(15) NOT NULL UNIQUE,
        asset_name VARCHAR(100),
        asset_type VARCHAR(20) DEFAULT 'EQUITY',
        currency VARCHAR(3) DEFAULT 'TRY'
    );
    """)

    # 2. Portfolios Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
        portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_name VARCHAR(50) NOT NULL,
        total_capital REAL NOT NULL,
        created_at DATE DEFAULT CURRENT_DATE
    );
    """)

    # 3. Portfolio Weights Tablosu
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

    # 4. Daily Prices Tablosu
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

    # Performans İndeksi
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_prices_asset_date 
    ON daily_prices(asset_id, price_date);
    """)

    # 5. SQL Görünümü (VIEW): LAG ve Moving Average Window Functions
    cursor.execute("""
    DROP VIEW IF EXISTS v_asset_daily_returns;
    """)
    
    cursor.execute("""
    CREATE VIEW v_asset_daily_returns AS
    WITH PriceLag AS (
        SELECT 
            dp.asset_id,
            a.ticker,
            dp.price_date,
            dp.adj_close,
            LAG(dp.adj_close, 1) OVER (
                PARTITION BY dp.asset_id 
                ORDER BY dp.price_date
            ) AS prev_close,
            AVG(dp.adj_close) OVER (
                PARTITION BY dp.asset_id 
                ORDER BY dp.price_date 
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS sma_20,
            AVG(dp.adj_close) OVER (
                PARTITION BY dp.asset_id 
                ORDER BY dp.price_date 
                ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
            ) AS sma_50
        FROM daily_prices dp
        JOIN assets a ON dp.asset_id = a.asset_id
    )
    SELECT 
        asset_id,
        ticker,
        price_date,
        adj_close,
        prev_close,
        sma_20,
        sma_50,
        CASE 
            WHEN prev_close IS NOT NULL AND prev_close > 0 
            THEN (adj_close - prev_close) / prev_close 
            ELSE NULL 
        END AS simple_return
    FROM PriceLag;
    """)

    conn.commit()
    conn.close()
    print("Veritabani tablolari ve analitik SQL gorunumleri (VIEW) basariyla guncellendi.")

if __name__ == "__main__":
    init_db()
