import os from "node:os";
import path from "node:path";

export const CREDENTIALS_PATH = "~/.eigenpoly/credentials.json";
export const CREDENTIALS_ABS_PATH = path.join(os.homedir(), ".eigenpoly", "credentials.json");

// Must be 32-byte base64 or 64-char hex in production.
export function readMasterKey(): Buffer {
  const raw = process.env.EIGENPOLY_MASTER_KEY;

  if (!raw) {
    throw new Error("EIGENPOLY_MASTER_KEY is required for credential encryption");
  }

  if (/^[a-f0-9]{64}$/i.test(raw)) {
    return Buffer.from(raw, "hex");
  }

  const key = Buffer.from(raw, "base64");
  if (key.length !== 32) {
    throw new Error("EIGENPOLY_MASTER_KEY must decode to exactly 32 bytes");
  }

  return key;
}
