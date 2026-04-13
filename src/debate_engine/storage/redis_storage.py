"""Redis storage backend for DebateEngine task persistence."""

import json
import logging
from typing import Any, Dict, Optional

import redis

from debate_engine.schemas import DebateJobSchema

logger = logging.getLogger(__name__)


class RedisStorage:
    """Redis-based storage for DebateEngine jobs."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis storage.

        Parameters
        ----------
        redis_url:
            Redis connection URL.
        """
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis storage")
        except Exception as exc:
            logger.warning("Failed to connect to Redis: %s. Falling back to in-memory storage", exc)
            self.redis_client = None

    def _get_key(self, job_id: str) -> str:
        """Get Redis key for a job."""
        return f"debate:job:{job_id}"

    def save_job(self, job: Any) -> bool:
        """Save a job to Redis.

        Parameters
        ----------
        job:
            DebateJob instance to save.

        Returns
        -------
        bool
            True if saved successfully, False otherwise.
        """
        if not self.redis_client:
            return False

        try:
            job_data = {
                "job_id": job.job_id,
                "config": job.config.model_dump() if hasattr(job.config, "model_dump") else job.config,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
                "current_round": job.current_round,
                "current_phase": job.current_phase,
                "progress_pct": job.progress_pct,
                "result": job.result.model_dump() if job.result and hasattr(job.result, "model_dump") else job.result,
                "error": job.error,
                "cost_so_far_usd": job.cost_so_far_usd,
                "cancel_requested": job.cancel_requested,
            }
            key = self._get_key(job.job_id)
            self.redis_client.setex(key, 3600, json.dumps(job_data, default=str))
            return True
        except Exception as exc:
            logger.warning("Failed to save job %s to Redis: %s", job.job_id, exc)
            return False

    def get_job(self, job_id: str) -> Optional[Any]:
        """Get a job from Redis.

        Parameters
        ----------
        job_id:
            Job ID to retrieve.

        Returns
        -------
        Optional[DebateJob]
            DebateJob instance if found, None otherwise.
        """
        from debate_engine.orchestration.debate import DebateJob
        
        if not self.redis_client:
            return None

        try:
            key = self._get_key(job_id)
            job_data = self.redis_client.get(key)
            if not job_data:
                return None

            data = json.loads(job_data)
            from datetime import datetime, timezone

            job = DebateJob(
                job_id=data["job_id"],
                config=data["config"],
                status=data["status"],
                created_at=datetime.fromisoformat(data["created_at"]).replace(tzinfo=timezone.utc),
                updated_at=datetime.fromisoformat(data["updated_at"]).replace(tzinfo=timezone.utc),
                current_round=data["current_round"],
                current_phase=data["current_phase"],
                progress_pct=data["progress_pct"],
                result=data["result"],
                error=data["error"],
                cost_so_far_usd=data["cost_so_far_usd"],
                cancel_requested=data["cancel_requested"],
            )
            return job
        except Exception as exc:
            logger.warning("Failed to get job %s from Redis: %s", job_id, exc)
            return None

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from Redis.

        Parameters
        ----------
        job_id:
            Job ID to delete.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        if not self.redis_client:
            return False

        try:
            key = self._get_key(job_id)
            self.redis_client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Failed to delete job %s from Redis: %s", job_id, exc)
            return False

    def list_jobs(self) -> list[str]:
        """List all job IDs in Redis.

        Returns
        -------
        list[str]
            List of job IDs.
        """
        if not self.redis_client:
            return []

        try:
            keys = self.redis_client.keys("debate:job:*")
            return [key.split(":")[-1] for key in keys]
        except Exception as exc:
            logger.warning("Failed to list jobs from Redis: %s", exc)
            return []

    def close(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception as exc:
                logger.warning("Failed to close Redis connection: %s", exc)
