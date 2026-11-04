"""Optional Redis cache keyed by corpus and ranking implementation version."""
import hashlib
import json


class SearchCache:
    def __init__(self, namespace, url=None, client=None, ttl=300):
        self.namespace = namespace
        self.ttl = ttl
        self.client = client
        if url and client is None:
            import redis
            self.client = redis.Redis.from_url(url, socket_connect_timeout=.25, socket_timeout=.25)

    def get_or_compute(self, parameters, compute):
        key = "rabbithole:search-v2:" + self.namespace + ":" + hashlib.sha256(
            json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        if self.client:
            try:
                cached = self.client.get(key)
                if cached is not None:
                    return json.loads(cached), "redis-hit"
            except (OSError, ValueError, ConnectionError):
                pass
            except Exception as exc:
                if not exc.__class__.__module__.startswith("redis"):
                    raise
        value = compute()
        if self.client:
            try:
                self.client.set(key, json.dumps(value, allow_nan=False), ex=self.ttl)
                return value, "redis-miss"
            except Exception as exc:
                if not isinstance(exc, OSError) and not exc.__class__.__module__.startswith("redis"):
                    raise
        return value, "uncached"
