import React, { useCallback } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { BiasBadge } from '../components/BiasBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { GradientButton } from '../components/GradientButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { useTrades } from '../hooks/useTrades';
import type { MainTabParamList, RootStackParamList } from '../navigation/types';
import { parseAnalysis } from '../storage/tradeRepository';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';
import { formatTimestamp } from '../utils/formatters';

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, 'Analysis'>,
  NativeStackScreenProps<RootStackParamList>
>;

function overallBiasLabel(bias: string): string {
  if (bias === 'BUY') return 'BULLISH';
  if (bias === 'SELL') return 'BEARISH';
  return 'NEUTRAL';
}

export function AnalysisHubScreen({ navigation }: Props) {
  const { trades, loading, refresh } = useTrades();

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  const latest = trades[0] ?? null;

  if (loading && !latest) {
    return (
      <ScreenContainer edges={['top', 'left', 'right']}>
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  if (!latest) {
    return (
      <ScreenContainer edges={['top', 'left', 'right']}>
        <View style={styles.header}>
          <Text style={styles.title}>AI Analysis</Text>
        </View>
        <View style={styles.empty}>
          <View style={styles.emptyIcon}>
            <Ionicons name="analytics-outline" size={36} color={colors.primary} />
          </View>
          <Text style={styles.emptyTitle}>No analysis yet</Text>
          <Text style={styles.emptyText}>
            Scan 4H, 1H, and 15M charts to generate your first AI Brain recommendation.
          </Text>
          <GradientButton
            label="Go to Scan"
            onPress={() => navigation.navigate('Scan')}
            style={styles.emptyCta}
          />
        </View>
      </ScreenContainer>
    );
  }

  const analysis = parseAnalysis(latest);
  const biasColor =
    latest.bias === 'BUY'
      ? colors.success
      : latest.bias === 'SELL'
        ? colors.danger
        : colors.noTrade;

  return (
    <ScreenContainer edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={styles.title}>AI Analysis</Text>
        <Text style={styles.subtitle}>{formatTimestamp(latest.createdAt)}</Text>
      </View>

      <Pressable
        style={styles.hero}
        onPress={() =>
          navigation.navigate('Results', {
            tradeId: latest.id,
            analysis,
          })
        }
      >
        <View style={styles.heroTop}>
          <Text style={styles.pair}>{latest.pair}</Text>
          <BiasBadge bias={latest.bias} />
        </View>
        <Text style={styles.biasLabel}>Overall Bias</Text>
        <Text style={[styles.biasValue, { color: biasColor }]}>
          {overallBiasLabel(latest.bias)}
        </Text>
        <ConfidenceBar value={latest.confidence} />
        <View style={styles.levels}>
          <Level label="Entry" value={latest.entry} />
          <Level label="SL" value={latest.stopLoss} danger />
          <Level label="TP" value={latest.takeProfit} success />
        </View>
        <Text style={styles.tapHint}>Tap for full result · View details</Text>
      </Pressable>
    </ScreenContainer>
  );
}

function Level({
  label,
  value,
  danger,
  success,
}: {
  label: string;
  value: string;
  danger?: boolean;
  success?: boolean;
}) {
  return (
    <View style={styles.level}>
      <Text style={styles.levelLabel}>{label}</Text>
      <Text
        style={[
          styles.levelValue,
          danger && { color: colors.danger },
          success && { color: colors.success },
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 8,
    marginBottom: 16,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 28,
  },
  subtitle: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    marginTop: 4,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  emptyIcon: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.primaryDim,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 18,
    marginBottom: 8,
  },
  emptyText: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  emptyCta: {
    alignSelf: 'stretch',
  },
  hero: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 20,
    padding: 18,
    gap: 10,
  },
  heroTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pair: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 20,
  },
  biasLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    marginTop: 4,
  },
  biasValue: {
    fontFamily: fonts.display,
    fontSize: 32,
    letterSpacing: 1,
  },
  levels: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  level: {
    flex: 1,
    backgroundColor: colors.surfaceElevated,
    borderRadius: 12,
    padding: 10,
  },
  levelLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 11,
  },
  levelValue: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 13,
    marginTop: 2,
  },
  tapHint: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 4,
  },
});
