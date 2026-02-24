import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

const ALGO = "aes-256-gcm";

export type CipherBlob = {
  iv: string;
  tag: string;
  value: string;
};

export function encryptString(plain: string, key: Buffer): CipherBlob {
  const iv = randomBytes(12);
  const cipher = createCipheriv(ALGO, key, iv);

  const value = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();

  return {
    iv: iv.toString("base64"),
    tag: tag.toString("base64"),
    value: value.toString("base64")
  };
}

export function decryptString(blob: CipherBlob, key: Buffer): string {
  const iv = Buffer.from(blob.iv, "base64");
  const tag = Buffer.from(blob.tag, "base64");
  const value = Buffer.from(blob.value, "base64");

  const decipher = createDecipheriv(ALGO, key, iv);
  decipher.setAuthTag(tag);

  const plain = Buffer.concat([decipher.update(value), decipher.final()]);
  return plain.toString("utf8");
}
