import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict


class EventBus:
    """
    Asynchronous High-Throughput Event Bus for Event-Driven Architecture.
    Supports events: TransactionCreated, TransactionFailed, PaymentSucceeded,
    RiskDetected, RecoveryTriggered, ActionExecuted, SettlementMismatch.
    """

    _instance: Optional["EventBus"] = None

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = defaultdict(list)
        self.event_history: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], Any]):
        self.subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        self.event_history.append(event)
        if len(self.event_history) > 1000:
            self.event_history.pop(0)

        # Notify subscribers
        for cb in self.subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(event))
                else:
                    cb(event)
            except Exception as e:
                print(f"Error notifying subscriber for {event_type}: {e}")

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self.event_history))[:limit]
