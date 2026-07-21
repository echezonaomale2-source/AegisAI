import * as SecureStore from 'expo-secure-store';

const API_URL_KEY = 'aegisai.api_base_url';
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';

let cachedUrl: string | null = null;

export function getDefaultApiBaseUrl(): string {
  return process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_API_BASE_URL;
}

export async function getApiBaseUrl(): Promise<string> {
  if (cachedUrl) {
    return cachedUrl;
  }
  try {
    const stored = await SecureStore.getItemAsync(API_URL_KEY);
    cachedUrl = (stored?.trim() || getDefaultApiBaseUrl()).replace(/\/$/, '');
  } catch {
    cachedUrl = getDefaultApiBaseUrl().replace(/\/$/, '');
  }
  return cachedUrl;
}

export async function setApiBaseUrl(url: string): Promise<void> {
  const normalized = url.trim().replace(/\/$/, '');
  await SecureStore.setItemAsync(API_URL_KEY, normalized);
  cachedUrl = normalized;
}

export async function clearApiBaseUrlOverride(): Promise<void> {
  await SecureStore.deleteItemAsync(API_URL_KEY);
  cachedUrl = null;
}

export const APP_VERSION = '11.0.0';
