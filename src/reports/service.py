"""Pure business calculations used by the dashboard and sales reports."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Dict, List, Tuple

from src.features.payments.billing_service import BillingService


class ReportingService:
    @staticmethod
    def _included_orders(
        orders: List[Mapping[str, Any]],
    ) -> List[Mapping[str, Any]]:
        return [order for order in orders if order.get("status") != "CANCELLED"]

    @staticmethod
    def order_item_count(order: Mapping[str, Any]) -> int:
        return sum(item["quantity"] for item in order["items"])

    @staticmethod
    def table_statuses(
        tables: Mapping[str, str],
        orders: List[Mapping[str, Any]],
        now: datetime | None = None,
    ) -> List[Dict[str, Any]]:
        active_orders = {
            order["table"]: order
            for order in ReportingService._included_orders(orders)
            if order["status"] != "PAID"
        }
        current_time = now or datetime.now()
        results = []
        for index, (table_id, source_status) in enumerate(tables.items(), start=1):
            order = active_orders.get(table_id)
            status = "Chờ thanh toán" if order and order["status"] == "READY" else source_status
            seated_time = "—"
            if order and order.get("created_at"):
                started_at = datetime.fromisoformat(order["created_at"])
                minutes = max(0, int((current_time - started_at).total_seconds() // 60))
                seated_time = f"{minutes} phút"
            results.append({
                "name": table_id,
                "seats": 4 if index % 3 else 6,
                "status": status,
                "seated_time": seated_time,
                "total": BillingService.calculate_total(order) if order else None,
            })
        return results

    @staticmethod
    def best_sellers(
        orders: List[Mapping[str, Any]],
        limit: int = 5,
    ) -> List[Tuple[str, int]]:
        counts: Counter[str] = Counter()
        for order in ReportingService._included_orders(orders):
            for item in order["items"]:
                counts[item["name"]] += item["quantity"]
        return counts.most_common(limit)

    @staticmethod
    def hourly_revenue(orders: List[Mapping[str, Any]]) -> Dict[str, int]:
        revenue = {f"{hour:02d}:00": 0 for hour in range(9, 19)}
        for order in ReportingService._included_orders(orders):
            if not order.get("created_at"):
                continue
            hour = datetime.fromisoformat(order["created_at"]).hour
            key = f"{hour:02d}:00"
            if key in revenue:
                revenue[key] += BillingService.calculate_total(order)
        return revenue

    @staticmethod
    def dashboard_alerts(
        orders: List[Mapping[str, Any]],
        requests: List[Any],
        now: datetime | None = None,
    ) -> List[str]:
        current_time = now or datetime.now()
        waiting_order_ids = {
            request.order_id
            for request in requests
            if request.status in {"NEW", "COOKING"}
        }
        delayed_items = 0
        long_seated_tables = 0
        for order in ReportingService._included_orders(orders):
            if not order.get("created_at"):
                continue
            elapsed = (current_time - datetime.fromisoformat(order["created_at"])).total_seconds() / 60
            if order["id"] in waiting_order_ids and elapsed > 15:
                delayed_items += sum(item["quantity"] for item in order["items"])
            if order["status"] != "PAID" and elapsed > 120:
                long_seated_tables += 1
        alerts = []
        if delayed_items:
            alerts.append(f"{delayed_items} món đang chờ bếp quá 15 phút.")
        if long_seated_tables:
            alerts.append(f"{long_seated_tables} bàn đã ngồi quá 2 giờ.")
        return alerts
