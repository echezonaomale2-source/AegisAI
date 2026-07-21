import {
  copyAsync,
  deleteAsync,
  documentDirectory,
  getInfoAsync,
  makeDirectoryAsync,
} from 'expo-file-system/legacy';
import { getImageExtension } from '../utils/imageValidation';

function getChartsDir(): string {
  if (!documentDirectory) {
    throw new Error('Document directory is unavailable on this platform.');
  }
  return `${documentDirectory}aegisai/charts/`;
}

async function ensureChartsDir(): Promise<string> {
  const chartsDir = getChartsDir();
  const info = await getInfoAsync(chartsDir);
  if (!info.exists) {
    await makeDirectoryAsync(chartsDir, { intermediates: true });
  }
  return chartsDir;
}

export async function persistChartImage(
  sourceUri: string,
  tradeId: string,
  label: '4h' | '1h' | '15m' | 'outcome',
): Promise<string> {
  const chartsDir = await ensureChartsDir();
  const extension = getImageExtension(sourceUri);
  const destination = `${chartsDir}${tradeId}_${label}.${extension}`;
  await copyAsync({ from: sourceUri, to: destination });
  return destination;
}

export async function deleteTradeImages(uris: Array<string | null | undefined>): Promise<void> {
  await Promise.all(
    uris.filter(Boolean).map(async (uri) => {
      try {
        const info = await getInfoAsync(uri!);
        if (info.exists) {
          await deleteAsync(uri!, { idempotent: true });
        }
      } catch {
        // Ignore missing files during cleanup.
      }
    }),
  );
}
