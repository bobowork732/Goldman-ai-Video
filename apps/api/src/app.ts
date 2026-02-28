import path from "node:path";

import express from "express";
import { ZodError } from "zod";

import { createAssetsRouter } from "./routes/assets.js";
import { createJobsRouter } from "./routes/jobs.js";
import { createJobQueue } from "./queue/job-queue.js";
import { PolicyRejectionError } from "./safety/policy-error.js";
import { createAssetStorage } from "./storage/asset-storage.js";

export function createApp() {
  const app = express();
  const queue = createJobQueue();
  const assetStorage = createAssetStorage();

  app.use(express.json());
  app.use("/storage", express.static(path.resolve(process.cwd(), "storage")));

  app.use("/jobs", createJobsRouter(queue));
  app.use("/assets", createAssetsRouter(assetStorage));

  app.use((error: unknown, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
    if (error instanceof ZodError) {
      return res.status(400).json({ message: "Validation failed", issues: error.issues });
    }

    if (error instanceof PolicyRejectionError) {
      return res.status(422).json(error.policy);
    }

    if (error instanceof Error && (error.message.startsWith("Model") || error.message.startsWith("Unsupported model"))) {
      return res.status(400).json({ message: error.message });
    }

    return res.status(500).json({ message: "Unexpected server error" });
  });

  return app;
}
