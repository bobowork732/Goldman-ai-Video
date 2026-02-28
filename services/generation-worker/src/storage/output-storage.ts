import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

export interface StoredObject {
  objectKey: string;
  publicUrl: string;
}

export interface OutputStorage {
  putObject(objectKey: string, body: Buffer, contentType: string): Promise<StoredObject>;
  putJson(objectKey: string, payload: unknown): Promise<StoredObject>;
}

export class LocalOutputStorage implements OutputStorage {
  private readonly rootDir: string;
  private readonly baseUrl: string;

  constructor() {
    this.rootDir = process.env.LOCAL_STORAGE_DIR ?? path.resolve(process.cwd(), "storage");
    this.baseUrl = process.env.LOCAL_STORAGE_BASE_URL ?? "http://localhost:3001/storage";
  }

  async putObject(objectKey: string, body: Buffer, _contentType: string): Promise<StoredObject> {
    const fullPath = path.resolve(this.rootDir, objectKey);
    await mkdir(path.dirname(fullPath), { recursive: true });
    await writeFile(fullPath, body);

    return {
      objectKey,
      publicUrl: `${this.baseUrl}/${encodeURIComponent(objectKey)}`
    };
  }

  async putJson(objectKey: string, payload: unknown): Promise<StoredObject> {
    return this.putObject(objectKey, Buffer.from(JSON.stringify(payload, null, 2), "utf8"), "application/json");
  }
}

export class S3CompatibleOutputStorage implements OutputStorage {
  private readonly bucketBaseUrl: string;

  constructor(bucketBaseUrl: string) {
    this.bucketBaseUrl = bucketBaseUrl;
  }

  async putObject(objectKey: string, _body: Buffer, _contentType: string): Promise<StoredObject> {
    return {
      objectKey,
      publicUrl: `${this.bucketBaseUrl.replace(/\/$/, "")}/${encodeURIComponent(objectKey)}`
    };
  }

  async putJson(objectKey: string, _payload: unknown): Promise<StoredObject> {
    return {
      objectKey,
      publicUrl: `${this.bucketBaseUrl.replace(/\/$/, "")}/${encodeURIComponent(objectKey)}`
    };
  }
}

export function createOutputStorage(): OutputStorage {
  const bucketUrl = process.env.S3_PUBLIC_BASE_URL;
  if (bucketUrl) {
    return new S3CompatibleOutputStorage(bucketUrl);
  }

  return new LocalOutputStorage();
}
