import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

export function issueApiKey(): string {
  return randomBytes(24).toString("base64url");
}

export function hashSignature(signature: string): string {
  return createHash("sha256").update(signature).digest("hex");
}

export function hashApiKey(apiKey: string): string {
  return createHash("sha256").update(apiKey).digest("hex");
}

export function verifyApiKey(provided: string, storedHash: string): boolean {
  const left = Buffer.from(hashApiKey(provided), "hex");
  const right = Buffer.from(storedHash, "hex");

  if (left.length !== right.length) {
    return false;
  }

  return timingSafeEqual(left, right);
}
