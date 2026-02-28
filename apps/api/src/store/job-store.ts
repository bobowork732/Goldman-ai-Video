import type { JobStatusResponse } from "@goldman-ai-video/shared";

const jobs = new Map<string, JobStatusResponse>();

export function saveJob(job: JobStatusResponse): void {
  jobs.set(job.id, job);
}

export function getJob(id: string): JobStatusResponse | undefined {
  return jobs.get(id);
}
