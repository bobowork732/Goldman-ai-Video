import { readFileSync } from "node:fs";
import path from "node:path";

import { Router } from "express";

import { assetProvenanceSchema } from "@goldman-ai-video/shared";

import type { AssetStorage } from "../storage/asset-storage.js";
import { getAsset } from "../store/asset-store.js";

function loadProvenanceFromSidecar(objectKey: string) {
  const sidecarName = objectKey.replace(/\.mp4$/i, ".provenance.json");
  const sidecarPath = path.resolve(process.cwd(), "storage", sidecarName);

  try {
    const raw = readFileSync(sidecarPath, "utf8");
    return assetProvenanceSchema.parse(JSON.parse(raw));
  } catch {
    return undefined;
  }
}

export function createAssetsRouter(assetStorage: AssetStorage): Router {
  const router = Router();

  router.get("/:id", async (req, res) => {
    const asset = getAsset(req.params.id);

    if (!asset) {
      return res.status(404).json({ message: "Asset not found" });
    }

    const url = asset.visibility === "public"
      ? assetStorage.getPublicUrl(asset.object_key)
      : await assetStorage.getSignedUrl(asset.object_key, 900);

    return res.json({
      id: asset.id,
      job_id: asset.job_id,
      mime_type: asset.mime_type,
      created_at: asset.created_at,
      url
    });
  });

  router.get("/:id/provenance", (req, res) => {
    const asset = getAsset(req.params.id);

    if (!asset) {
      return res.status(404).json({ message: "Asset provenance not found" });
    }

    const provenance = asset.provenance ?? loadProvenanceFromSidecar(asset.object_key);

    if (!provenance) {
      return res.status(404).json({ message: "Asset provenance not found" });
    }

    return res.json({
      asset_id: asset.id,
      metadata_hash: provenance.job_hash,
      lineage: provenance.lineage,
      model_id: provenance.model_id,
      model_version: provenance.model_version,
      generated_at: provenance.generated_at,
      job_id: provenance.job_id
    });
  });

  return router;
}
