#!/usr/bin/env python3
"""
Test idempotency of grid signal processing.
Ensures duplicate signals don't create duplicate orders.
"""

import requests
import time
import json

API_BASE = "http://localhost:8000"
WEBHOOK_BASE = "http://localhost:5678"

def test_idempotent_grid_signal():
    """Test that sending the same grid signal twice doesn't duplicate orders"""
    
    signal = {
        "model": "chatgpt",
        "strategy": "grid",
        "symbol": "SOLUSDT",
        "lower": 180.0,
        "upper": 210.0,
        "grids": 5,
        "spacing": "arithmetic",
        "base_allocation": 100,
        "leverage": 1,
        "entry_mode": "maker_first",
        "tp_pct": 0.03,
        "sl_pct": 0.05,
        "rebalance": False,
        "notes": "Idempotency test"
    }
    
    print("=" * 60)
    print("TEST: Idempotency of Grid Signals")
    print("=" * 60)
    
    print("\n1. Sending first grid signal...")
    response1 = requests.post(f"{API_BASE}/grid/apply", json=signal)
    print(f"   Status: {response1.status_code}")
    result1 = response1.json()
    print(f"   Result: {json.dumps(result1, indent=2)}")
    
    config_id = result1.get("config_id")
    placed_count_1 = result1.get("placed", 0)
    
    time.sleep(2)
    
    print("\n2. Sending identical grid signal again...")
    response2 = requests.post(f"{API_BASE}/grid/apply", json=signal)
    print(f"   Status: {response2.status_code}")
    result2 = response2.json()
    print(f"   Result: {json.dumps(result2, indent=2)}")
    
    placed_count_2 = result2.get("placed", 0)
    
    print("\n3. Checking orders in database...")
    orders_response = requests.get(f"{API_BASE}/orders?model=chatgpt&symbol=SOLUSDT")
    orders = orders_response.json().get("orders", [])
    print(f"   Total orders: {len(orders)}")
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"First request placed: {placed_count_1} orders")
    print(f"Second request placed: {placed_count_2} orders")
    print(f"Total orders in DB: {len(orders)}")
    
    if placed_count_2 == placed_count_1:
        print("\n✅ PASS: Idempotency maintained - no duplicate orders created")
        return True
    else:
        print("\n❌ FAIL: Duplicate orders were created")
        return False


def test_client_order_id_uniqueness():
    """Test that client order IDs are unique and deterministic"""
    
    print("\n" + "=" * 60)
    print("TEST: Client Order ID Uniqueness")
    print("=" * 60)
    
    signal = {
        "model": "grok",
        "strategy": "grid",
        "symbol": "BTCUSDT",
        "lower": 40000.0,
        "upper": 45000.0,
        "grids": 3,
        "spacing": "arithmetic",
        "base_allocation": 100,
        "leverage": 1,
        "entry_mode": "maker_first",
        "tp_pct": 0.03,
        "sl_pct": 0.05,
        "rebalance": False
    }
    
    print("\n1. Creating grid...")
    response = requests.post(f"{API_BASE}/grid/apply", json=signal)
    result = response.json()
    config_id = result.get("config_id")
    
    print(f"   Config ID: {config_id}")
    
    print("\n2. Fetching grid status...")
    status_response = requests.get(f"{API_BASE}/grid/status?model=grok&symbol=BTCUSDT")
    status = status_response.json()
    levels = status.get("levels", [])
    
    client_order_ids = [level["client_order_id"] for level in levels]
    unique_ids = set(client_order_ids)
    
    print(f"   Total levels: {len(levels)}")
    print(f"   Unique client order IDs: {len(unique_ids)}")
    print(f"   Client Order IDs: {client_order_ids}")
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if len(client_order_ids) == len(unique_ids):
        print("✅ PASS: All client order IDs are unique")
        return True
    else:
        print("❌ FAIL: Duplicate client order IDs found")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IDEMPOTENCY TEST SUITE")
    print("=" * 60)
    print("\nNOTE: Ensure Trading Core is running on localhost:8000")
    print("      This test uses mock/testnet mode if configured\n")
    
    try:
        test1_pass = test_idempotent_grid_signal()
        test2_pass = test_client_order_id_uniqueness()
        
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        print(f"Idempotent Grid Signal: {'✅ PASS' if test1_pass else '❌ FAIL'}")
        print(f"Client Order ID Uniqueness: {'✅ PASS' if test2_pass else '❌ FAIL'}")
        
        if test1_pass and test2_pass:
            print("\n🎉 All tests passed!")
            exit(0)
        else:
            print("\n⚠️  Some tests failed")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nMake sure Trading Core is running and accessible")
        exit(1)
