import redis.asyncio as redis
import json
from typing import Optional, Dict, Any

class RedisCacheBase:
    """Базовый класс для всех кэшей с общими методами."""
    def __init__(self, redis_client: redis.Redis, prefix: str, ttl: int = 300):
        self.redis = redis_client
        self.prefix = prefix  # Например, "user", "model", "cooldown"
        self.ttl = ttl

    async def get(self, entity_id: int) -> Optional[Dict[str, Any]]:
        raw = await self.redis.get(f"{self.prefix}:{entity_id}")
        return json.loads(raw) if raw else None

    async def set(self, entity_id: int, data: Dict[str, Any]):
        await self.redis.set(
            f"{self.prefix}:{entity_id}", 
            json.dumps(data), 
            ex=self.ttl
        )

    async def delete(self, entity_id: int):
        await self.redis.delete(f"{self.prefix}:{entity_id}")


class RedisUserCache(RedisCacheBase):
    """Кэш данных пользователя."""
    def __init__(self, redis_client: redis.Redis, ttl: int = 300):
        super().__init__(redis_client, "user", ttl)


class RedisActiveModelCache(RedisCacheBase):
    """Кэш активной модели пользователя."""
    def __init__(self, redis_client: redis.Redis, ttl: int = 300):
        super().__init__(redis_client, "model", ttl)


class RedisUserCooldown:
    """Кэш кулдаунов (можно было бы через RedisCacheBase, но тут логика особенная)."""
    def __init__(self, redis_client: redis.Redis, cooldown_seconds: int):
        self.redis = redis_client
        self.cooldown = cooldown_seconds

    async def is_on_cooldown(self, user_id: int) -> bool:
        return await self.redis.exists(f"cooldown:{user_id}") == 1

    async def set_cooldown(self, user_id: int):
        await self.redis.set(f"cooldown:{user_id}", "1", ex=self.cooldown)


class RedisGenParamsCache(RedisCacheBase):
    """Кэш параметров генерации."""
    def __init__(self, redis_client: redis.Redis, ttl: int = 300):
        super().__init__(redis_client, "params", ttl)