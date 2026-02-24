import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { CREDENTIALS_ABS_PATH, CREDENTIALS_PATH, readMasterKey } from "../config";
import { encryptString, type CipherBlob } from "./crypto";

export type StoredCredential = {
  agentId: string;
  walletAddress: string;
  signatureHash: string;
  apiKeyHash: string;
  encryptedApiKey: CipherBlob;
  createdAt: string;
  updatedAt: string;
};

type CredentialFile = {
  version: number;
  records: StoredCredential[];
};

const EMPTY_FILE: CredentialFile = {
  version: 1,
  records: []
};

async function readCredentialFile(): Promise<CredentialFile> {
  try {
    const raw = await readFile(CREDENTIALS_ABS_PATH, "utf8");
    return JSON.parse(raw) as CredentialFile;
  } catch (error) {
    const err = error as NodeJS.ErrnoException;
    if (err.code === "ENOENT") {
      return EMPTY_FILE;
    }
    throw error;
  }
}

async function writeCredentialFile(file: CredentialFile): Promise<void> {
  await mkdir(path.dirname(CREDENTIALS_ABS_PATH), { recursive: true });
  await writeFile(CREDENTIALS_ABS_PATH, `${JSON.stringify(file, null, 2)}\n`, { mode: 0o600 });
}

export async function upsertCredentialRecord(input: {
  agentId: string;
  walletAddress: string;
  signatureHash: string;
  apiKey: string;
  apiKeyHash: string;
}): Promise<{ canonicalPath: string; absolutePath: string }> {
  const file = await readCredentialFile();
  const now = new Date().toISOString();
  const key = readMasterKey();

  const encryptedApiKey = encryptString(input.apiKey, key);
  const next: StoredCredential = {
    agentId: input.agentId,
    walletAddress: input.walletAddress,
    signatureHash: input.signatureHash,
    apiKeyHash: input.apiKeyHash,
    encryptedApiKey,
    createdAt: now,
    updatedAt: now
  };

  const idx = file.records.findIndex((r) => r.agentId === input.agentId);
  if (idx >= 0) {
    next.createdAt = file.records[idx].createdAt;
    file.records[idx] = next;
  } else {
    file.records.push(next);
  }

  await writeCredentialFile(file);

  return {
    canonicalPath: CREDENTIALS_PATH,
    absolutePath: CREDENTIALS_ABS_PATH
  };
}

export async function readCredentialFileRecord(agentId: string): Promise<StoredCredential | null> {
  const file = await readCredentialFile();
  return file.records.find((record) => record.agentId === agentId) ?? null;
}
