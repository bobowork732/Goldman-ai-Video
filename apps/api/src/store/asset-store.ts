import type { AssetProvenance } from "@goldman-ai-video/shared";

export interface AssetRecord {
  id: string;
  job_id: string;
  object_key: string;
  mime_type: string;
  created_at: string;
  visibility: "public" | "signed";
  provenance?: AssetProvenance;
}

const assets = new Map<string, AssetRecord>();

export function saveAsset(asset: AssetRecord): void {
  assets.set(asset.id, asset);
}

export function getAsset(id: string): AssetRecord | undefined {
  return assets.get(id);
}
