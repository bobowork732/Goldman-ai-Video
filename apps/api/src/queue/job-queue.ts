import Redis from "ioredis";

import type { WorkerJobContract } from "@goldman-ai-video/shared";

export const DEFAULT_QUEUE_KEY = "video-generation:jobs";

export interface JobQueue {
  enqueue(job: WorkerJobContract): Promise<void>;
}

export class InMemoryJobQueue implements JobQueue {
  private readonly jobs: WorkerJobContract[] = [];

  async enqueue(job: WorkerJobContract): Promise<void> {
    this.jobs.push(job);
  }

  snapshot(): WorkerJobContract[] {
    return [...this.jobs];
  }
}

export class RedisJobQueue implements JobQueue {
  constructor(private readonly redis: Redis, private readonly queueKey: string = DEFAULT_QUEUE_KEY) {}

  async enqueue(job: WorkerJobContract): Promise<void> {
    await this.redis.lpush(this.queueKey, JSON.stringify(job));
  }
}

export function createJobQueue(): JobQueue {
  const redisUrl = process.env.REDIS_URL;

  if (!redisUrl) {
    return new InMemoryJobQueue();
  }

  const redis = new Redis(redisUrl, { maxRetriesPerRequest: 1 });
  return new RedisJobQueue(redis);
}
