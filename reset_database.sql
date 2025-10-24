
DELETE FROM orders;

DELETE FROM positions;

DELETE FROM llm_decisions;

DELETE FROM metrics;

DELETE FROM grid_levels;

DELETE FROM grid_configs;

DELETE FROM price_history WHERE timestamp < NOW() - INTERVAL '1 hour';

UPDATE model_accounts SET 
    initial_balance = 500.0,
    current_balance = 500.0,
    total_pnl = 0.0,
    updated_at = NOW()
WHERE model IN ('chatgpt', 'grok', 'claude', 'deepseek');

SELECT model, initial_balance, current_balance, total_pnl FROM model_accounts;
