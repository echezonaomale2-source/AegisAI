import React, { useCallback } from 'react';
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { BiasBadge } from '../components/BiasBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { GradientButton } from '../components/GradientButton';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { useTrade } from '../hooks/useTrades';
import type { RootStackParamList } from '../navigation/types';
import { parseAnalysis } from '../storage/tradeRepository';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';
import { formatTimestamp, outcomeLabel } from '../utils/formatters';

type Props = NativeStackScreenProps<RootStackParamList, 'TradeDetails'>;

export function TradeDetailsScreen({ navigation, route }: Props) {
  const { tradeId } = route.params;
  const { trade, loading, refresh } = useTrade(tradeId);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  if (loading || !trade) {
    return (
      <ScreenContainer>
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </ScreenContainer>
    );
  }

  const analysis = parseAnalysis(trade);
  const observations = [
    analysis.analysis4h.marketStructure !== 'Neutral'
      ? `Structure: ${analysis.analysis4h.marketStructure}`
      : null,
    analysis.analysis4h.liquidity !== 'None Detected'
      ? `Liquidity: ${analysis.analysis4h.liquidity}`
      : null,
    analysis.analysis4h.orderBlock !== 'None Detected'
      ? `Order block: ${analysis.analysis4h.orderBlock}`
      : null,
    analysis.analysis4h.fvg !== 'None Detected' ? `FVG: ${analysis.analysis4h.fvg}` : null,
    ...analysis.analysis15m.reasons.slice(0, 4),
  ].filter(Boolean) as string[];

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.top}>
          <Text style={styles.heading}>Detailed Analysis</Text>
          <Text style={styles.timestamp}>{formatTimestamp(trade.createdAt)}</Text>
        </View>

        <View style={styles.hero}>
          <View style={styles.heroTop}>
            <View>
              <Text style={styles.pair}>{trade.pair}</Text>
              <Text style={styles.status}>{outcomeLabel(trade.outcome)}</Text>
            </View>
            <BiasBadge bias={trade.bias} />
          </View>
          <ConfidenceBar value={trade.confidence} />
        </View>

        <Text style={styles.tfHeader}>4H TIMEFRAME</Text>
        <ConfidenceBar
          value={Math.max(50, trade.confidence - 2)}
          label="4H Confidence"
          color={colors.primary}
        />

        <View style={styles.chartCard}>
          <Image source={{ uri: trade.chart4hUri }} style={styles.chartImage} resizeMode="cover" />
          <View style={styles.annoRow}>
            <Anno label="BOS / Structure" />
            <Anno label="Liquidity" />
            <Anno label="Order Block" />
          </View>
        </View>

        <View style={styles.block}>
          <Text style={styles.blockTitle}>Market Structure</Text>
          <Text style={styles.blockBody}>
            {analysis.analysis4h.summary ||
              `${analysis.analysis4h.trend} bias with ${analysis.analysis4h.marketStructure}.`}
          </Text>
        </View>

        <View style={styles.block}>
          <Text style={styles.blockTitle}>Key Observations</Text>
          {observations.length === 0 ? (
            <Text style={styles.blockBody}>No strong observations recorded.</Text>
          ) : (
            observations.map((item) => (
              <View key={item} style={styles.obsRow}>
                <Ionicons name="checkmark-circle" size={18} color={colors.success} />
                <Text style={styles.obsText}>{item}</Text>
              </View>
            ))
          )}
        </View>

        <View style={styles.summaryBox}>
          <Text style={styles.summaryLabel}>Summary</Text>
          <Text style={styles.summaryText}>
            {analysis.explanation || analysis.finalDecision || trade.finalDecision}
          </Text>
        </View>

        <Text style={styles.tfHeader}>1H · 15M Charts</Text>
        <ChartPreview label="1H" uri={trade.chart1hUri} />
        <ChartPreview label="15M" uri={trade.chart15mUri} />

        {trade.outcomeChartUri ? (
          <ChartPreview label="Outcome" uri={trade.outcomeChartUri} />
        ) : null}

        <View style={styles.setupCard}>
          <Text style={styles.blockTitle}>Trade Levels</Text>
          <LevelRow label="Entry" value={trade.entry} />
          <LevelRow label="Stop Loss" value={trade.stopLoss} color={colors.danger} />
          <LevelRow label="Take Profit" value={trade.takeProfit} color={colors.success} />
          <LevelRow label="Risk Reward" value={trade.riskReward} />
        </View>

        {trade.status === 'WAITING' ? (
          <GradientButton
            label="Upload Trade Outcome"
            onPress={() => navigation.navigate('UploadOutcome', { tradeId: trade.id })}
          />
        ) : null}

        <PrimaryButton
          label="Back"
          mode="outlined"
          color={colors.textSecondary}
          onPress={() => navigation.goBack()}
        />
      </ScrollView>
    </ScreenContainer>
  );
}

function Anno({ label }: { label: string }) {
  return (
    <View style={styles.anno}>
      <Text style={styles.annoText}>{label}</Text>
    </View>
  );
}

function ChartPreview({ label, uri }: { label: string; uri: string }) {
  return (
    <View style={styles.chartCard}>
      <Text style={styles.chartLabel}>{label}</Text>
      <Image source={{ uri }} style={styles.chartImageSmall} resizeMode="cover" />
    </View>
  );
}

function LevelRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <View style={styles.levelRow}>
      <Text style={styles.levelLabel}>{label}</Text>
      <Text style={[styles.levelValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingTop: 8,
    paddingBottom: 36,
    gap: 12,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  top: {
    marginBottom: 4,
  },
  heading: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 26,
  },
  timestamp: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    marginTop: 4,
  },
  hero: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    gap: 12,
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
  status: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    marginTop: 2,
  },
  tfHeader: {
    color: colors.primary,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
    letterSpacing: 1,
    marginTop: 8,
  },
  chartCard: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    padding: 12,
    gap: 10,
  },
  chartImage: {
    width: '100%',
    height: 200,
    borderRadius: 12,
    backgroundColor: colors.surfaceElevated,
  },
  chartImageSmall: {
    width: '100%',
    height: 140,
    borderRadius: 10,
    backgroundColor: colors.surfaceElevated,
  },
  chartLabel: {
    color: colors.textSecondary,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
  },
  annoRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  anno: {
    backgroundColor: colors.primaryDim,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  annoText: {
    color: colors.primary,
    fontFamily: fonts.bodyMedium,
    fontSize: 11,
  },
  block: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    gap: 10,
  },
  blockTitle: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 15,
  },
  blockBody: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 21,
  },
  obsRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  obsText: {
    flex: 1,
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 19,
  },
  summaryBox: {
    backgroundColor: colors.surfaceElevated,
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  summaryLabel: {
    color: colors.primary,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
    marginBottom: 6,
  },
  summaryText: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 21,
  },
  setupCard: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    gap: 10,
  },
  levelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  levelLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 13,
  },
  levelValue: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 14,
  },
});
