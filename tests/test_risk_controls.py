#!/usr/bin/env python3
"""
Test risk control mechanisms.
Ensures leverage, exposure, and daily loss limits are enforced.
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_leverage_limit():
    """Test that excessive leverage is rejected"""
    
    print("=" * 60)
    print("TEST: Leverage Limit Enforcement")
    print("=" * 60)
    
    signal = {
        "model": "chatgpt",
        "strategy": "grid",
        "symbol": "ETHUSDT",
        "lower": 2000.0,
        "upper": 2500.0,
        "grids": 5,
        "spacing": "arithmetic",
        "base_allocation": 1000,
        "leverage": 10,
        "entry_mode": "maker_first",
        "tp_pct": 0.03,
        "sl_pct": 0.05,
        "rebalance": False,
        "notes": "Testing excessive leverage"
    }
    
    print(f"\n1. Attempting to create grid with leverage={signal['leverage']}...")
    print(f"   (Max allowed leverage: 2)")
    
    response = requests.post(f"{API_BASE}/grid/apply", json=signal)
    result = response.json()
    
    print(f"   Status: {response.status_code}")
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if result.get("status") == "error" and "leverage" in result.get("message", "").lower():
        print("✅ PASS: Excessive leverage was rejected")
        return True
    else:
        print("❌ FAIL: Excessive leverage was not rejected")
        return False


def test_exposure_limit():
    """Test that excessive exposure is rejected"""
    
    print("\n" + "=" * 60)
    print("TEST: Exposure Limit Enforcement")
    print("=" * 60)
    
    signal = {
        "model": "grok",
        "strategy": "grid",
        "symbol": "BNBUSDT",
        "lower": 300.0,
        "upper": 400.0,
        "grids": 5,
        "spacing": "arithmetic",
        "base_allocation": 10000,
        "leverage": 2,
        "entry_mode": "maker_first",
        "tp_pct": 0.03,
        "sl_pct": 0.05,
        "rebalance": False,
        "notes": "Testing excessive exposure"
    }
    
    total_exposure = signal["base_allocation"] * signal["leverage"]
    
    print(f"\n1. Attempting to create grid with exposure={total_exposure}...")
    print(f"   (Max allowed exposure: 5000)")
    
    response = requests.post(f"{API_BASE}/grid/apply", json=signal)
    result = response.json()
    
    print(f"   Status: {response.status_code}")
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if result.get("status") == "error" and "exposure" in result.get("message", "").lower():
        print("✅ PASS: Excessive exposure was rejected")
        return True
    else:
        print("❌ FAIL: Excessive exposure was not rejected")
        return False


def test_valid_grid_accepted():
    """Test that a valid grid within all limits is accepted"""
    
    print("\n" + "=" * 60)
    print("TEST: Valid Grid Acceptance")
    print("=" * 60)
    
    signal = {
        "model": "chatgpt",
        "strategy": "grid",
        "symbol": "SOLUSDT",
        "lower": 180.0,
        "upper": 210.0,
        "grids": 5,
        "spacing": "arithmetic",
        "base_allocation": 500,
        "leverage": 2,
        "entry_mode": "maker_first",
        "tp_pct": 0.03,
        "sl_pct": 0.05,
        "rebalance": False,
        "notes": "Testing valid grid"
    }
    
    total_exposure = signal["base_allocation"] * signal["leverage"]
    
    print(f"\n1. Creating valid grid...")
    print(f"   Leverage: {signal['leverage']} (max: 2)")
    print(f"   Exposure: {total_exposure} (max: 5000)")
    
    response = requests.post(f"{API_BASE}/grid/apply", json=signal)
    result = response.json()
    
    print(f"   Status: {response.status_code}")
    print(f"   Result: {json.dumps(result, indent=2)}")
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if result.get("status") == "ok" and result.get("config_id"):
        print("✅ PASS: Valid grid was accepted")
        return True
    else:
        print("❌ FAIL: Valid grid was rejected")
        return False


def test_grid_pause_resume():
    """Test grid pause and resume functionality"""
    
    print("\n" + "=" * 60)
    print("TEST: Grid Pause/Resume")
    print("=" * 60)
    
    model = "chatgpt"
    symbol = "SOLUSDT"
    
    print(f"\n1. Pausing grid for {model}/{symbol}...")
    pause_response = requests.post(f"{API_BASE}/grid/pause?model={model}&symbol={symbol}")
    pause_result = pause_response.json()
    print(f"   Status: {pause_response.status_code}")
    print(f"   Result: {json.dumps(pause_result, indent=2)}")
    
    print(f"\n2. Checking grid status...")
    status_response = requests.get(f"{API_BASE}/grid/status?model={model}&symbol={symbol}")
    
    if status_response.status_code == 200:
        status = status_response.json()
        config_status = status.get("config", {}).get("status")
        print(f"   Grid status: {config_status}")
        
        if config_status == "paused":
            print("\n3. Resuming grid...")
            resume_response = requests.post(f"{API_BASE}/grid/resume?model={model}&symbol={symbol}")
            resume_result = resume_response.json()
            print(f"   Status: {resume_response.status_code}")
            print(f"   Result: {json.dumps(resume_result, indent=2)}")
            
            status_response2 = requests.get(f"{API_BASE}/grid/status?model={model}&symbol={symbol}")
            if status_response2.status_code == 200:
                status2 = status_response2.json()
                config_status2 = status2.get("config", {}).get("status")
                print(f"   Grid status after resume: {config_status2}")
                
                print("\n" + "=" * 60)
                print("RESULTS:")
                print("=" * 60)
                
                if config_status2 == "active":
                    print("✅ PASS: Grid pause/resume works correctly")
                    return True
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print("❌ FAIL: Grid pause/resume failed")
    return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RISK CONTROLS TEST SUITE")
    print("=" * 60)
    print("\nNOTE: Ensure Trading Core is running on localhost:8000")
    print("      Risk limits configured in trading-core/.env\n")
    
    try:
        test1_pass = test_leverage_limit()
        test2_pass = test_exposure_limit()
        test3_pass = test_valid_grid_accepted()
        test4_pass = test_grid_pause_resume()
        
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        print(f"Leverage Limit: {'✅ PASS' if test1_pass else '❌ FAIL'}")
        print(f"Exposure Limit: {'✅ PASS' if test2_pass else '❌ FAIL'}")
        print(f"Valid Grid Acceptance: {'✅ PASS' if test3_pass else '❌ FAIL'}")
        print(f"Grid Pause/Resume: {'✅ PASS' if test4_pass else '❌ FAIL'}")
        
        if test1_pass and test2_pass and test3_pass and test4_pass:
            print("\n🎉 All tests passed!")
            exit(0)
        else:
            print("\n⚠️  Some tests failed")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nMake sure Trading Core is running and accessible")
        exit(1)
