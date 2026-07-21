import { useCallback, useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import { Alert } from 'react-native';
import type { ChartUploads } from '../types/analysis';
import { isValidChartImage } from '../utils/imageValidation';

export type ChartSlot = keyof ChartUploads;

const emptyUploads: ChartUploads = {
  chart4h: null,
  chart1h: null,
  chart15m: null,
};

export function useChartUploads() {
  const [uploads, setUploads] = useState<ChartUploads>(emptyUploads);

  const pickImage = useCallback(async (slot: ChartSlot) => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission required', 'Allow photo library access to upload charts.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: false,
      quality: 1,
    });

    if (result.canceled || !result.assets?.[0]) {
      return;
    }

    const asset = result.assets[0];
    if (!isValidChartImage(asset.uri, asset.mimeType)) {
      Alert.alert('Invalid image', 'Only PNG, JPG, and JPEG files are accepted.');
      return;
    }

    setUploads((prev) => ({ ...prev, [slot]: asset.uri }));
  }, []);

  const clearImage = useCallback((slot: ChartSlot) => {
    setUploads((prev) => ({ ...prev, [slot]: null }));
  }, []);

  const resetUploads = useCallback(() => {
    setUploads(emptyUploads);
  }, []);

  const allUploaded = Boolean(uploads.chart4h && uploads.chart1h && uploads.chart15m);

  return {
    uploads,
    pickImage,
    clearImage,
    resetUploads,
    allUploaded,
  };
}
