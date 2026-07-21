import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import {
  APP_VERSION,
  clearApiBaseUrlOverride,
  getApiBaseUrl,
  getDefaultApiBaseUrl,
  setApiBaseUrl,
} from '../config/appConfig';
import type { MainTabParamList, RootStackParamList } from '../navigation/types';
import { healthCheck } from '../services/api';
import { flushOutcomeSyncQueue, pendingSyncCount } from '../storage/syncQueue';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, 'Settings'>,
  NativeStackScreenProps<RootStackParamList>
>;

export function SettingsScreen({ navigation }: Props) {
  const [apiUrl, setApiUrl] = useState(getDefaultApiBaseUrl());
  const [health, setHealth] = useState<{ ok: boolean; version?: string; detail?: string } | null>(
    null,
  );
  const [pending, setPending] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const url = await getApiBaseUrl();
    setApiUrl(url);
    setPending(await pendingSyncCount());
    setHealth(await healthCheck());
  }, []);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onSaveUrl = async () => {
    setBusy(true);
    setMessage(null);
    try {
      await setApiBaseUrl(apiUrl);
      const result = await healthCheck();
      setHealth(result);
      setMessage(result.ok ? 'API URL saved — backend reachable.' : 'Saved, but backend unreachable.');
    } finally {
      setBusy(false);
    }
  };

  const onResetUrl = async () => {
    await clearApiBaseUrlOverride();
    setApiUrl(getDefaultApiBaseUrl());
    setMessage('Reset to default API URL.');
    void refresh();
  };

  const onFlush = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await flushOutcomeSyncQueue();
      setPending(await pendingSyncCount());
      setMessage(`Synced ${result.flushed} · failed ${result.failed}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Sync failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScreenContainer edges={['top', 'left', 'right']}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Settings</Text>
        <Text style={styles.subtitle}>AegisAI Personal · v{APP_VERSION}</Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Backend connection</Text>
          <View style={styles.healthRow}>
            <View
              style={[
                styles.dot,
                { backgroundColor: health?.ok ? colors.success : colors.danger },
              ]}
            />
            <Text style={styles.healthText}>
              {health == null
                ? 'Checking…'
                : health.ok
                  ? `Online${health.version ? ` · API ${health.version}` : ''}`
                  : `Offline · ${health.detail ?? 'unreachable'}`}
            </Text>
          </View>
          <Text style={styles.label}>API base URL</Text>
          <TextInput
            value={apiUrl}
            onChangeText={setApiUrl}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder={getDefaultApiBaseUrl()}
            placeholderTextColor={colors.textMuted}
            style={styles.input}
          />
          <PrimaryButton label="Save & Check Health" onPress={() => void onSaveUrl()} loading={busy} />
          <PrimaryButton
            label="Reset to Default"
            mode="outlined"
            color={colors.textSecondary}
            onPress={() => void onResetUrl()}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Offline sync</Text>
          <Text style={styles.meta}>{pending} outcome(s) waiting to sync</Text>
          <PrimaryButton
            label="Flush Sync Queue"
            onPress={() => void onFlush()}
            loading={busy}
            disabled={pending === 0}
          />
        </View>

        <View style={styles.card}>
          <SettingsRow
            icon="hardware-chip-outline"
            title="AI Memory"
            subtitle="Patterns, grades & lessons"
            onPress={() => navigation.navigate('Memory')}
          />
          <SettingsRow
            icon="bulb-outline"
            title="Research Insights"
            subtitle="Calibration & system health"
            onPress={() => navigation.navigate('Insights')}
          />
          <SettingsRow
            icon="scan-outline"
            title="New Chart Scan"
            subtitle="Upload 4H · 1H · 15M"
            onPress={() => navigation.navigate('Scan')}
            last
          />
        </View>

        <View style={styles.card}>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Engine</Text>
            <Text style={styles.infoValue}>AI Brain</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Local encryption</Text>
            <Text style={styles.infoValue}>AES-CTR analysis payloads</Text>
          </View>
          <View style={[styles.infoRow, styles.infoRowLast]}>
            <Text style={styles.infoLabel}>Concepts</Text>
            <Text style={styles.infoValue}>Smart Money only</Text>
          </View>
        </View>

        {message ? <Text style={styles.message}>{message}</Text> : null}

        <Text style={styles.footer}>
          Prefer NO TRADE over low-quality setups. The Brain never invents missing evidence.
        </Text>
      </ScrollView>
    </ScreenContainer>
  );
}

function SettingsRow({
  icon,
  title,
  subtitle,
  onPress,
  last,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  onPress: () => void;
  last?: boolean;
}) {
  return (
    <Pressable style={[styles.row, !last && styles.rowBorder]} onPress={onPress}>
      <View style={styles.rowIcon}>
        <Ionicons name={icon} size={20} color={colors.primary} />
      </View>
      <View style={styles.rowText}>
        <Text style={styles.rowTitle}>{title}</Text>
        <Text style={styles.rowSubtitle}>{subtitle}</Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { paddingTop: 8, paddingBottom: 36, gap: 16 },
  title: { color: colors.text, fontFamily: fonts.display, fontSize: 28 },
  subtitle: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 13, marginTop: -8 },
  card: {
    backgroundColor: colors.card,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    overflow: 'hidden',
    padding: 14,
    gap: 10,
  },
  cardTitle: { color: colors.text, fontFamily: fonts.displayMedium, fontSize: 16 },
  healthRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  healthText: { color: colors.textSecondary, fontFamily: fonts.body, fontSize: 13, flex: 1 },
  label: { color: colors.textMuted, fontFamily: fonts.bodyMedium, fontSize: 12 },
  input: {
    backgroundColor: colors.surfaceElevated,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: colors.text,
    fontFamily: fonts.body,
    fontSize: 14,
  },
  meta: { color: colors.textSecondary, fontFamily: fonts.body, fontSize: 13 },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, gap: 12 },
  rowBorder: { borderBottomWidth: 1, borderBottomColor: colors.surfaceBorder },
  rowIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: colors.primaryDim,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rowText: { flex: 1 },
  rowTitle: { color: colors.text, fontFamily: fonts.bodyBold, fontSize: 15 },
  rowSubtitle: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 12, marginTop: 2 },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceBorder,
  },
  infoRowLast: { borderBottomWidth: 0 },
  infoLabel: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 14 },
  infoValue: { color: colors.text, fontFamily: fonts.bodyMedium, fontSize: 14 },
  message: { color: colors.primary, fontFamily: fonts.body, fontSize: 13, textAlign: 'center' },
  footer: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
    paddingHorizontal: 12,
  },
});
