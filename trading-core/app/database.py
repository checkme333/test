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
                    CREATE TABLE IF NOT EXISTS model_accounts (
                        id SERIAL PRIMARY KEY,
                        model TEXT UNIQUE NOT NULL,
                        initial_balance NUMERIC NOT NULL,
                        current_balance NUMERIC NOT NULL,
                        total_pnl NUMERIC DEFAULT 0,
                        total_trades INT DEFAULT 0,
                        winning_trades INT DEFAULT 0,
                        losing_trades INT DEFAULT 0,
                        max_drawdown NUMERIC DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS llm_decisions (
                        id SERIAL PRIMARY KEY,
                        model TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        decision_type TEXT NOT NULL,
                        action TEXT NOT NULL,
                        reasoning TEXT,
                        market_data JSONB,
                        decision_data JSONB,
                        executed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS price_history (
                        id SERIAL PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        price NUMERIC NOT NULL,
                        volume NUMERIC,
                        timestamp TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        id SERIAL PRIMARY KEY,
                        model TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        size NUMERIC NOT NULL,
                        entry_price NUMERIC NOT NULL,
                        current_price NUMERIC,
                        unrealized_pnl NUMERIC DEFAULT 0,
                        leverage INT DEFAULT 1,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(model, symbol)
                    );
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_llm_decisions_model_ts 
                    ON llm_decisions(model, created_at DESC);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_price_history_symbol_ts 
                    ON price_history(symbol, timestamp DESC);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_positions_model 
                    ON positions(model);
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
    
    def init_model_account(self, model: str, initial_balance: float):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO model_accounts (model, initial_balance, current_balance)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (model) DO NOTHING;
                """, (model, initial_balance, initial_balance))
    
    def get_model_account(self, model: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM model_accounts WHERE model = %s;
                """, (model,))
                return cur.fetchone()
    
    def get_all_model_accounts(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM model_accounts ORDER BY total_pnl DESC;
                """)
                return cur.fetchall()
    
    def update_model_balance(self, model: str, balance: float, pnl: float):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE model_accounts 
                    SET current_balance = %s, 
                        total_pnl = %s,
                        updated_at = NOW()
                    WHERE model = %s;
                """, (balance, pnl, model))
    
    def insert_llm_decision(self, decision: Dict[str, Any]):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO llm_decisions 
                    (model, symbol, decision_type, action, reasoning, market_data, decision_data, executed)
                    VALUES (%(model)s, %(symbol)s, %(decision_type)s, %(action)s, 
                            %(reasoning)s, %(market_data)s, %(decision_data)s, %(executed)s)
                    RETURNING id;
                """, decision)
                result = cur.fetchone()
                return result['id']
    
    def get_recent_decisions(self, model: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if model:
                    cur.execute("""
                        SELECT * FROM llm_decisions 
                        WHERE model = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s;
                    """, (model, limit))
                else:
                    cur.execute("""
                        SELECT * FROM llm_decisions 
                        ORDER BY created_at DESC 
                        LIMIT %s;
                    """, (limit,))
                return cur.fetchall()
    
    def insert_price(self, symbol: str, price: float, volume: Optional[float] = None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO price_history (symbol, price, volume)
                    VALUES (%s, %s, %s);
                """, (symbol, price, volume))
    
    def get_price_history(self, symbol: str, hours: int = 1) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM price_history 
                    WHERE symbol = %s 
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp ASC;
                """, (symbol, hours))
                return cur.fetchall()
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM price_history 
                    WHERE symbol = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 1;
                """, (symbol,))
                return cur.fetchone()
    
    def upsert_position(self, position: Dict[str, Any]):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO positions 
                    (model, symbol, side, size, entry_price, current_price, unrealized_pnl, leverage)
                    VALUES (%(model)s, %(symbol)s, %(side)s, %(size)s, %(entry_price)s, 
                            %(current_price)s, %(unrealized_pnl)s, %(leverage)s)
                    ON CONFLICT (model, symbol) DO UPDATE SET
                        side = EXCLUDED.side,
                        size = EXCLUDED.size,
                        entry_price = EXCLUDED.entry_price,
                        current_price = EXCLUDED.current_price,
                        unrealized_pnl = EXCLUDED.unrealized_pnl,
                        leverage = EXCLUDED.leverage,
                        updated_at = NOW();
                """, position)
    
    def get_positions(self, model: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if model:
                    cur.execute("""
                        SELECT * FROM positions WHERE model = %s;
                    """, (model,))
                else:
                    cur.execute("""
                        SELECT * FROM positions;
                    """)
                return cur.fetchall()
    
    def close_position(self, model: str, symbol: str):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM positions WHERE model = %s AND symbol = %s;
                """, (model, symbol))
    
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
