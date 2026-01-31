#!/usr/bin/env python3
"""Show Kiroku Memory system status."""

import json
import os
import sys
import urllib.request
import urllib.error

KIROKU_API = os.environ.get("KIROKU_API", "http://localhost:8000")


def get_health() -> dict:
    """Get basic health status."""
    url = f"{KIROKU_API}/health"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_detailed_health() -> dict:
    """Get detailed health status with counts."""
    url = f"{KIROKU_API}/health/detailed"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_metrics() -> dict:
    """Get application metrics."""
    url = f"{KIROKU_API}/metrics"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_categories() -> list:
    """Get all categories."""
    url = f"{KIROKU_API}/categories"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=== Kiroku Memory 狀態 ===\n")

    try:
        # Basic health
        health = get_health()
        status = health.get("status", "unknown")
        version = health.get("version", "?")
        status_icon = "✓" if status == "ok" else "✗"
        print(f"服務狀態: {status_icon} {status} (v{version})")
        print(f"API 位址: {KIROKU_API}")
        print()

    except urllib.error.URLError:
        print(f"✗ 無法連接 Kiroku Memory API ({KIROKU_API})")
        print()
        print("請確認服務已啟動：")
        print("  cd ~/zoo/kiroku-memory")
        print("  docker compose up -d")
        print("  uv run uvicorn kiroku_memory.api:app --reload")
        sys.exit(1)

    try:
        # Detailed health
        detailed = get_detailed_health()
        checks = detailed.get("checks", {})
        data = checks.get("data", {})

        active_items = data.get("active_items", 0)
        resources = data.get("resources", 0)
        embeddings = data.get("embeddings", 0)

        print("--- 記憶統計 ---")
        print(f"  原始資源: {resources}")
        print(f"  活躍項目: {active_items}")
        print(f"  嵌入向量: {embeddings}")
        print()

    except Exception as e:
        print(f"  (無法取得詳細統計: {e})")
        print()

    try:
        # Categories
        categories = get_categories()
        if categories:
            print("--- 分類 ---")
            for cat in categories:
                name = cat.get("name", "")
                summary = cat.get("summary", "")
                has_summary = "✓" if summary else "○"
                print(f"  {has_summary} {name}")
            print()

    except Exception:
        pass

    try:
        # Metrics
        metrics = get_metrics()
        counters = metrics.get("counters", {})
        latencies = metrics.get("latencies", {})

        if counters:
            print("--- 操作計數 ---")
            print(f"  攝取: {counters.get('ingest_count', 0)}")
            print(f"  抽取: {counters.get('extract_count', 0)}")
            print(f"  檢索: {counters.get('retrieve_count', 0)}")
            print(f"  錯誤: {counters.get('error_count', 0)}")
            print()

        if latencies:
            p50 = latencies.get("retrieve_p50", 0)
            p95 = latencies.get("retrieve_p95", 0)
            if p50 or p95:
                print("--- 延遲 (ms) ---")
                print(f"  檢索 P50: {p50:.1f}")
                print(f"  檢索 P95: {p95:.1f}")

    except Exception:
        pass


if __name__ == "__main__":
    main()
