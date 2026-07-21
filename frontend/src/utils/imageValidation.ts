const ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg'] as const;

export function isValidChartImage(uri: string, mimeType?: string | null): boolean {
  const lowerUri = uri.toLowerCase();
  const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) => lowerUri.includes(ext));

  if (mimeType) {
    const allowedMimes = ['image/png', 'image/jpeg', 'image/jpg'];
    return allowedMimes.includes(mimeType.toLowerCase()) || hasValidExtension;
  }

  return hasValidExtension;
}

export function getImageExtension(uri: string): string {
  const lower = uri.toLowerCase();
  if (lower.includes('.png')) return 'png';
  if (lower.includes('.jpeg')) return 'jpeg';
  return 'jpg';
}
