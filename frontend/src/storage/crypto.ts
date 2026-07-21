/**
 * Local field encryption for sensitive SQLite payloads.
 * Key lives in expo-secure-store; ciphertext uses AES-CTR (aes-js).
 */
import * as SecureStore from 'expo-secure-store';
import * as ExpoCrypto from 'expo-crypto';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const aesjs = require('aes-js');

const KEY_ID = 'aegisai.encryption_key.v1';
const PREFIX = 'enc:v1:';

async function getOrCreateKey(): Promise<Uint8Array> {
  const existing = await SecureStore.getItemAsync(KEY_ID);
  if (existing) {
    return Uint8Array.from(existing.split(',').map((n) => Number(n)));
  }
  const bytes = await ExpoCrypto.getRandomBytesAsync(32);
  await SecureStore.setItemAsync(KEY_ID, Array.from(bytes).join(','));
  return bytes;
}

function toHex(bytes: Uint8Array): string {
  return aesjs.utils.hex.fromBytes(bytes);
}

function fromHex(hex: string): Uint8Array {
  return aesjs.utils.hex.toBytes(hex);
}

export function isEncrypted(value: string): boolean {
  return value.startsWith(PREFIX);
}

export async function encryptText(plaintext: string): Promise<string> {
  const key = await getOrCreateKey();
  const iv = await ExpoCrypto.getRandomBytesAsync(16);
  const textBytes = aesjs.utils.utf8.toBytes(plaintext);
  const aesCtr = new aesjs.ModeOfOperation.ctr(key, new aesjs.Counter(iv));
  const encrypted = aesCtr.encrypt(textBytes);
  return `${PREFIX}${toHex(iv)}:${toHex(encrypted)}`;
}

export async function decryptText(value: string): Promise<string> {
  if (!isEncrypted(value)) {
    return value;
  }
  const body = value.slice(PREFIX.length);
  const [ivHex, dataHex] = body.split(':');
  if (!ivHex || !dataHex) {
    throw new Error('Corrupted encrypted payload');
  }
  const key = await getOrCreateKey();
  const iv = fromHex(ivHex);
  const encrypted = fromHex(dataHex);
  const aesCtr = new aesjs.ModeOfOperation.ctr(key, new aesjs.Counter(iv));
  const decrypted = aesCtr.decrypt(encrypted);
  return aesjs.utils.utf8.fromBytes(decrypted);
}
