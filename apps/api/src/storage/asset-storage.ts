export interface AssetStorage {
  getPublicUrl(objectKey: string): string;
  getSignedUrl(objectKey: string, expiresInSeconds: number): Promise<string>;
}

export class LocalAssetStorage implements AssetStorage {
  constructor(private readonly baseUrl: string = process.env.LOCAL_STORAGE_BASE_URL ?? "http://localhost:3001/storage") {}

  getPublicUrl(objectKey: string): string {
    return `${this.baseUrl}/${encodeURIComponent(objectKey)}`;
  }

  async getSignedUrl(objectKey: string, expiresInSeconds: number): Promise<string> {
    const url = new URL(this.getPublicUrl(objectKey));
    url.searchParams.set("expires_in", String(expiresInSeconds));
    return url.toString();
  }
}

export class S3CompatibleAssetStorage implements AssetStorage {
  constructor(private readonly bucketBaseUrl: string) {}

  getPublicUrl(objectKey: string): string {
    return `${this.bucketBaseUrl.replace(/\/$/, "")}/${encodeURIComponent(objectKey)}`;
  }

  async getSignedUrl(objectKey: string, expiresInSeconds: number): Promise<string> {
    const url = new URL(this.getPublicUrl(objectKey));
    url.searchParams.set("signature", "mock-signature");
    url.searchParams.set("expires_in", String(expiresInSeconds));
    return url.toString();
  }
}

export function createAssetStorage(): AssetStorage {
  const s3BaseUrl = process.env.S3_PUBLIC_BASE_URL;

  if (s3BaseUrl) {
    return new S3CompatibleAssetStorage(s3BaseUrl);
  }

  return new LocalAssetStorage();
}
