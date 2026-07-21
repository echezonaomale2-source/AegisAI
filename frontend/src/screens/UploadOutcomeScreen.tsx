import React, { useState } from 'react';
import {
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { GradientButton } from '../components/GradientButton';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { useTrade } from '../hooks/useTrades';
import type { RootStackParamList } from '../navigation/types';
import { persistChartImage } from '../storage/imageStorage';
import { updateTradeOutcome } from '../storage/tradeRepository';
import { submitTradeOutcome } from '../services/api';
import type { TradeOutcome } from '../types/analysis';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';
import { isValidChartImage } from '../utils/imageValidation';

type Props = NativeStackScreenProps<RootStackParamList, 'UploadOutcome'>;

type OutcomeChoice = Exclude<TradeOutcome, null>;

export function UploadOutcomeScreen({ navigation, route }: Props) {
  const { tradeId } = route.params;
  const { trade } = useTrade(tradeId);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<OutcomeChoice | null>(null);
  const [comments, setComments] = useState('');
  const [rrAchieved, setRrAchieved] = useState('');
  const [saving, setSaving] = useState(false);

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission required', 'Allow photo library access to upload the result chart.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
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

    setImageUri(asset.uri);
  };

  const onSave = async () => {
    if (!imageUri || !outcome) {
      Alert.alert('Incomplete', 'Upload an after-trade chart and select an outcome.');
      return;
    }

    const persistedOutcome: Exclude<TradeOutcome, null> = outcome;

    setSaving(true);
    try {
      const savedUri = await persistChartImage(imageUri, tradeId, 'outcome');
      await updateTradeOutcome(tradeId, persistedOutcome, savedUri, {
        comments: comments || undefined,
        rrAchieved: rrAchieved || undefined,
        syncStatus: 'pending',
      });

      try {
        const learned = await submitTradeOutcome({
          tradeId,
          outcome: persistedOutcome,
          resultChartUri: imageUri,
          comments: comments || undefined,
          rrAchieved: rrAchieved || undefined,
        });
        await updateTradeOutcome(tradeId, persistedOutcome, savedUri, {
          syncStatus: 'synced',
        });
        const gradeLine = learned.grade
          ? `Grade ${learned.grade}${learned.grade_label ? ` (${learned.grade_label})` : ''}.\n\n`
          : '';
        Alert.alert(
          'Submitted',
          `${gradeLine}${learned.lesson || 'Outcome saved — AI Memory updated.'}`,
        );
      } catch {
        const { enqueueOutcomeSync } = await import('../storage/syncQueue');
        await enqueueOutcomeSync({
          tradeId,
          outcome: persistedOutcome,
          resultChartUri: imageUri,
          comments: comments || undefined,
          rrAchieved: rrAchieved || undefined,
        });
        Alert.alert(
          'Saved locally — queued for sync',
          'Outcome is on device. Open Settings → Flush Sync Queue when the backend is reachable.',
        );
      }
      navigation.replace('TradeDetails', { tradeId });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save outcome.';
      Alert.alert('Save failed', message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Upload Trade Outcome</Text>
        <Text style={styles.subtitle}>
          Log the result so the AI Brain can learn from this setup.
        </Text>

        {trade ? (
          <View style={styles.summary}>
            <Text style={styles.summaryPair}>
              {trade.pair} · {trade.bias}
            </Text>
            <Text style={styles.summaryMeta}>
              Entry {trade.entry} · SL {trade.stopLoss} · TP {trade.takeProfit}
            </Text>
          </View>
        ) : null}

        <Text style={styles.sectionLabel}>After Trade Chart</Text>
        {imageUri ? (
          <View style={styles.previewWrap}>
            <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="cover" />
            <Pressable onPress={() => void pickImage()}>
              <Text style={styles.replace}>Replace Image</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable style={styles.uploadArea} onPress={() => void pickImage()}>
            <Ionicons name="cloud-upload-outline" size={28} color={colors.primary} />
            <Text style={styles.uploadTitle}>Upload After Chart</Text>
            <Text style={styles.uploadHint}>PNG · JPG · JPEG</Text>
          </Pressable>
        )}

        <Text style={styles.sectionLabel}>Outcome</Text>
        <View style={styles.choiceCol}>
          <OutcomeChip
            label="Take Profit Hit"
            active={outcome === 'TAKE_PROFIT'}
            color={colors.success}
            onPress={() => setOutcome('TAKE_PROFIT')}
          />
          <OutcomeChip
            label="Stop Loss Hit"
            active={outcome === 'STOP_LOSS'}
            color={colors.danger}
            onPress={() => setOutcome('STOP_LOSS')}
          />
          <OutcomeChip
            label="Break Even"
            active={outcome === 'BREAK_EVEN'}
            color={colors.warning}
            onPress={() => setOutcome('BREAK_EVEN')}
          />
        </View>

        <Text style={styles.sectionLabel}>RR Achieved</Text>
        <TextInput
          value={rrAchieved}
          onChangeText={setRrAchieved}
          placeholder="e.g. 1:2.1"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
        />

        <Text style={styles.sectionLabel}>Comments</Text>
        <TextInput
          value={comments}
          onChangeText={setComments}
          placeholder="Clean liquidity sweep and strong continuation…"
          placeholderTextColor={colors.textMuted}
          multiline
          style={[styles.input, styles.comments]}
        />

        <GradientButton
          label="Submit & Improve AI"
          onPress={() => void onSave()}
          loading={saving}
          disabled={!imageUri || !outcome}
        />
        <PrimaryButton
          label="Cancel"
          mode="outlined"
          color={colors.textSecondary}
          onPress={() => navigation.goBack()}
        />
      </ScrollView>
    </ScreenContainer>
  );
}

function OutcomeChip({
  label,
  active,
  color,
  onPress,
}: {
  label: string;
  active: boolean;
  color: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[
        styles.choice,
        active && { borderColor: color, backgroundColor: `${color}22` },
      ]}
      onPress={onPress}
    >
      <Text style={[styles.choiceText, active && { color }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingTop: 8,
    paddingBottom: 36,
    gap: 12,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 26,
  },
  subtitle: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 4,
  },
  summary: {
    backgroundColor: colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    padding: 14,
    gap: 4,
  },
  summaryPair: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 16,
  },
  summaryMeta: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
  },
  sectionLabel: {
    color: colors.textSecondary,
    fontFamily: fonts.bodyMedium,
    fontSize: 12,
    marginTop: 4,
  },
  uploadArea: {
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: 'rgba(124, 92, 255, 0.45)',
    borderRadius: 16,
    backgroundColor: colors.primaryDim,
    minHeight: 140,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  uploadTitle: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 15,
  },
  uploadHint: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
  },
  previewWrap: {
    gap: 10,
  },
  preview: {
    width: '100%',
    height: 180,
    borderRadius: 14,
    backgroundColor: colors.surfaceElevated,
  },
  replace: {
    color: colors.primary,
    fontFamily: fonts.bodyMedium,
  },
  choiceCol: {
    gap: 10,
  },
  choice: {
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: colors.card,
  },
  choiceText: {
    color: colors.textSecondary,
    fontFamily: fonts.bodyBold,
    fontSize: 14,
  },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: colors.text,
    fontFamily: fonts.body,
    fontSize: 14,
  },
  comments: {
    minHeight: 96,
    textAlignVertical: 'top',
  },
});
