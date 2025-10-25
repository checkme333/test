import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
from app.config import settings
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    def __init__(self):
        self.conn_string = settings.database_url
    
    @contextmanager
    def get_connection(self):
        conn = psycopg.connect(self.conn_string, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_schema(self):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS grid_configs (
                        id SERIAL PRIMARY KEY,
                        model TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        lower NUMERIC NOT NULL,
                        upper NUMERIC NOT NULL,
                        grids INT NOT NULL,
                        spacing TEXT NOT NULL,
                        base_allocation NUMERIC NOT NULL,
                        leverage INT NOT NULL,
                        tp_pct NUMERIC NOT NULL,
                        sl_pct NUMERIC NOT NULL,
                        rebalance BOOLEAN NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(model, symbol)
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS grid_levels (
                        id SERIAL PRIMARY KEY,
                        config_id INT REFERENCES grid_configs(id) ON DELETE CASCADE,
                        level_idx INT NOT NULL,
                        price NUMERIC NOT NULL,
                        side TEXT NOT NULL,
                        qty NUMERIC NOT NULL,
                        client_order_id TEXT UNIQUE NOT NULL,
                        state TEXT NOT NULL DEFAULT 'planned',
                        last_error TEXT,
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id SERIAL PRIMARY KEY,
                        model TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        client_order_id TEXT UNIQUE NOT NULL,
                        exchange_order_id TEXT,
                        side TEXT NOT NULL,
                        price NUMERIC NOT NULL,
                        qty NUMERIC NOT NULL,
                        fill_qty NUMERIC DEFAULT 0,
                        status TEXT NOT NULL,
                        fee NUMERIC DEFAULT 0,
                        pnl NUMERIC DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        ts TIMESTAMP NOT NULL,
                        model TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        pnl NUMERIC NOT NULL,
                        daily_pnl NUMERIC NOT NULL,
                        win_rate NUMERIC NOT NULL,
                        max_drawdown NUMERIC NOT NULL,
                        exposure NUMERIC NOT NULL,
                        PRIMARY KEY (ts, model, symbol)
                    );
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_orders_model_symbol 
                    ON orders(model, symbol);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metrics_model_ts 
                    ON metrics(model, ts DESC);
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pnl_snapshots (
                        id SERIAL PRIMARY KEY,
                        model TEXT NOT NULL,
                        pnl NUMERIC NOT NULL,
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE(model, timestamp)
                    );
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pnl_snapshots_model_ts 
                    ON pnl_snapshots(model, timestamp DESC);
                """)
    
    def upsert_grid_config(self, config: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO grid_configs 
                    (model, symbol, lower, upper, grids, spacing, base_allocation, 
                     leverage, tp_pct, sl_pct, rebalance, status, updated_at)
                    VALUES (%(model)s, %(symbol)s, %(lower)s, %(upper)s, %(grids)s, 
                            %(spacing)s, %(base_allocation)s, %(leverage)s, %(tp_pct)s, 
                            %(sl_pct)s, %(rebalance)s, %(status)s, NOW())
                    ON CONFLICT (model, symbol) 
                    DO UPDATE SET 
                        lower = EXCLUDED.lower,
                        upper = EXCLUDED.upper,
                        grids = EXCLUDED.grids,
                        spacing = EXCLUDED.spacing,
                        base_allocation = EXCLUDED.base_allocation,
                        leverage = EXCLUDED.leverage,
                        tp_pct = EXCLUDED.tp_pct,
                        sl_pct = EXCLUDED.sl_pct,
                        rebalance = EXCLUDED.rebalance,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    RETURNING id;
                """, config)
                result = cur.fetchone()
                return result['id']
    
    def get_grid_config(self, model: str, symbol: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM grid_configs 
                    WHERE model = %s AND symbol = %s;
                """, (model, symbol))
                return cur.fetchone()
    
    def insert_grid_level(self, level: Dict[str, Any]):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO grid_levels 
                    (config_id, level_idx, price, side, qty, client_order_id, state, updated_at)
                    VALUES (%(config_id)s, %(level_idx)s, %(price)s, %(side)s, 
                            %(qty)s, %(client_order_id)s, %(state)s, NOW())
                    ON CONFLICT (client_order_id) DO NOTHING;
                """, level)
    
    def update_grid_level_state(self, client_order_id: str, state: str, error: Optional[str] = None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE grid_levels 
                    SET state = %s, last_error = %s, updated_at = NOW()
                    WHERE client_order_id = %s;
                """, (state, error, client_order_id))
    
    def get_grid_levels(self, config_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM grid_levels 
                    WHERE config_id = %s 
                    ORDER BY level_idx;
                """, (config_id,))
                return cur.fetchall()
    
    def insert_order(self, order: Dict[str, Any]):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO orders 
                    (model, symbol, client_order_id, exchange_order_id, side, 
                     price, qty, fill_qty, status, fee, pnl, created_at, updated_at)
                    VALUES (%(model)s, %(symbol)s, %(client_order_id)s, %(exchange_order_id)s,
                            %(side)s, %(price)s, %(qty)s, %(fill_qty)s, %(status)s, 
                            %(fee)s, %(pnl)s, NOW(), NOW())
                    ON CONFLICT (client_order_id) DO UPDATE SET
                        exchange_order_id = EXCLUDED.exchange_order_id,
                        fill_qty = EXCLUDED.fill_qty,
                        status = EXCLUDED.status,
                        fee = EXCLUDED.fee,
                        pnl = EXCLUDED.pnl,
                        updated_at = NOW();
                """, order)
    
    def get_orders(self, model: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                query = "SELECT * FROM orders WHERE 1=1"
                params = []
                if model:
                    query += " AND model = %s"
                    params.append(model)
                if symbol:
                    query += " AND symbol = %s"
                    params.append(symbol)
                query += " ORDER BY created_at DESC LIMIT 1000;"
                cur.execute(query, params)
                return cur.fetchall()
    
    def insert_metrics(self, metrics: Dict[str, Any]):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO metrics 
                    (ts, model, symbol, pnl, daily_pnl, win_rate, max_drawdown, exposure)
                    VALUES (%(ts)s, %(model)s, %(symbol)s, %(pnl)s, %(daily_pnl)s, 
                            %(win_rate)s, %(max_drawdown)s, %(exposure)s)
                    ON CONFLICT (ts, model, symbol) DO UPDATE SET
                        pnl = EXCLUDED.pnl,
                        daily_pnl = EXCLUDED.daily_pnl,
                        win_rate = EXCLUDED.win_rate,
                        max_drawdown = EXCLUDED.max_drawdown,
                        exposure = EXCLUDED.exposure;
                """, metrics)
    
    def get_metrics(self, model: Optional[str] = None, window: str = "all") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                query = "SELECT * FROM metrics WHERE 1=1"
                params = []
                if model:
                    query += " AND model = %s"
                    params.append(model)
                
                if window == "daily":
                    query += " AND ts >= NOW() - INTERVAL '1 day'"
                elif window == "weekly":
                    query += " AND ts >= NOW() - INTERVAL '7 days'"
                
                query += " ORDER BY ts DESC LIMIT 1000;"
                cur.execute(query, params)
                return cur.fetchall()
    
    def update_grid_status(self, model: str, symbol: str, status: str):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE grid_configs 
                    SET status = %s, updated_at = NOW()
                    WHERE model = %s AND symbol = %s;
                """, (status, model, symbol))
    
    def insert_pnl_snapshot(self, model: str, pnl: float, timestamp: Optional[datetime] = None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if timestamp is None:
                    cur.execute("""
                        INSERT INTO pnl_snapshots (model, pnl, timestamp)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (model, timestamp) DO UPDATE SET pnl = EXCLUDED.pnl;
                    """, (model, pnl))
                else:
                    cur.execute("""
                        INSERT INTO pnl_snapshots (model, pnl, timestamp)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (model, timestamp) DO UPDATE SET pnl = EXCLUDED.pnl;
                    """, (model, pnl, timestamp))
    
    def get_pnl_snapshots(self, model: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if model:
                    cur.execute("""
                        SELECT model, pnl, timestamp 
                        FROM pnl_snapshots 
                        WHERE model = %s AND timestamp >= NOW() - INTERVAL '%s hours'
                        ORDER BY timestamp ASC;
                    """, (model, hours))
                else:
                    cur.execute("""
                        SELECT model, pnl, timestamp 
                        FROM pnl_snapshots 
                        WHERE timestamp >= NOW() - INTERVAL '%s hours'
                        ORDER BY timestamp ASC;
                    """, (hours,))
                return cur.fetchall()


db = Database()
