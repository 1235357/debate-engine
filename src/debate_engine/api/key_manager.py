"""API Key Manager for load balancing and failover."""

import threading
import time
from collections import defaultdict


class APIKeyManager:
    """Manage multiple API keys with load balancing and failover."""

    def __init__(self, api_keys: list[str]) -> None:
        self.api_keys = api_keys
        self.current_index = 0
        self.lock = threading.Lock()
        self.key_stats: dict[str, dict] = defaultdict(
            lambda: {
                "success_count": 0,
                "failure_count": 0,
                "last_used": 0,
                "last_failed": 0,
                "is_active": True,
            }
        )
        self.cooldown_period = 60

    def get_next_key(self) -> str:
        """Get the next available API key for load balancing."""
        with self.lock:
            if not self.api_keys:
                return ""

            # 按成功率排序密钥
            def key_score(key):
                stats = self.key_stats[key]
                total = stats["success_count"] + stats["failure_count"]
                if total == 0:
                    return 1.0
                return stats["success_count"] / total

            sorted_keys = sorted(self.api_keys, key=key_score, reverse=True)

            # 查找第一个可用的密钥
            for key in sorted_keys:
                stats = self.key_stats[key]
                if stats["is_active"]:
                    if stats["last_failed"] > 0:
                        time_since_failure = time.time() - stats["last_failed"]
                        if time_since_failure < self.cooldown_period:
                            continue
                    # 密钥可用
                    stats["last_used"] = time.time()
                    return key

            # 回退：返回第一个密钥
            key = self.api_keys[0]
            self.key_stats[key]["last_used"] = time.time()
            return key

    def record_success(self, api_key: str) -> None:
        """Record a successful API call for a key."""
        with self.lock:
            if api_key in self.key_stats:
                self.key_stats[api_key]["success_count"] += 1
                self.key_stats[api_key]["is_active"] = True

    def record_failure(self, api_key: str) -> None:
        """Record a failed API call for a key."""
        with self.lock:
            if api_key in self.key_stats:
                self.key_stats[api_key]["failure_count"] += 1
                self.key_stats[api_key]["last_failed"] = time.time()
                # If failure rate is too high, mark as inactive
                stats = self.key_stats[api_key]
                total = stats["success_count"] + stats["failure_count"]
                if total > 10 and stats["failure_count"] / total > 0.5:
                    stats["is_active"] = False

    def get_stats(self) -> dict[str, dict]:
        """Get statistics for all API keys."""
        with self.lock:
            return dict(self.key_stats)
