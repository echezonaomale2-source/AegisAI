import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { BiasBadge } from '../components/BiasBadge';
import { ConfidenceBar } from '../components/ConfidenceBar';
import { GradientButton } from '../components/GradientButton';
import { ScreenContainer } from '../components/ScreenContainer';
import type { RootStackParamList } from '../navigation/types';
import type { TradeBias, TrendBias } from '../types/analysis';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'Results'>;

function overallBiasLabel(bias: TradeBias): string {
  if (bias === 'BUY') return 'BULLISH';
  if (bias === 'SELL') return 'BEARISH';
  return 'NEUTRAL';
}

function trendTone(trend: TrendBias): string {
  if (trend === 'Bullish') return colors.success;
  if (trend === 'Bearish') return colors.danger;
  return colors.noTrade;
}

function qualityFromConfidence(confidence: number): string {
  if (confidence >= 80) return 'High';
  if (confidence >= 65) return 'Medium';
  return 'Low';
}

function estimatePips(entry: string, tp: string): string {
  const e = Number.parseFloat(entry);
  const t = Number.parseFloat(tp);
  if (!Number.isFinite(e) || !Number.isFinite(t)) return '—';
  const diff = Math.abs(t - e);
  // FX-style pip approx when price has 4–5 decimals; otherwise show points
  if (e < 50) {
    return `${Math.round(diff * 10000)} Pips`;
  }
  return `${diff.toFixed(2)} Pts`;
}

export function ResultsScreen({ navigation, route }: Props) {
  const { tradeId, analysis } = route.params;
  const htf = analysis.timeframes?.HTF || analysis.timeframes?.['4H'] || '4H';
  const mtf = analysis.timeframes?.MTF || analysis.timeframes?.['1H'] || '1H';
  const ltf = analysis.timeframes?.LTF || analysis.timeframes?.['15M'] || '15M';
  const biasColor =
    analysis.bias === 'BUY'
      ? colors.success
      : analysis.bias === 'SELL'
        ? colors.danger
        : colors.noTrade;

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <View>
            <Text style={styles.heading}>AI Analysis Result</Text>
            <Text style={styles.pair}>{analysis.pair}</Text>
          </View>
          <BiasBadge bias={analysis.bias} />
        </View>

        <View style={styles.hero}>
          <Text style={styles.biasLabel}>Overall Bias</Text>
          <Text style={[styles.biasValue, { color: biasColor }]}>
            {overallBiasLabel(analysis.bias)}
          </Text>
          <ConfidenceBar value={analysis.confidence} />
        </View>

        <Text style={styles.sectionTitle}>Multi-Timeframe</Text>
        <View style={styles.tfRow}>
          <TfCard
            tf={htf}
            label={analysis.analysis4h.trend.toUpperCase()}
            color={trendTone(analysis.analysis4h.trend)}
            confidence={Math.max(50, analysis.confidence - 2)}
            onPress={() => navigation.navigate('TradeDetails', { tradeId })}
          />
          <TfCard
            tf={mtf}
            label={analysis.analysis1h.trend.toUpperCase()}
            color={trendTone(analysis.analysis1h.trend)}
            confidence={Math.max(50, analysis.confidence - 1)}
            onPress={() => navigation.navigate('TradeDetails', { tradeId })}
          />
          <TfCard
            tf={ltf}
            label={analysis.bias === 'NO TRADE' ? 'NO SETUP' : `${analysis.bias} SETUP`}
            color={biasColor}
            confidence={analysis.confidence}
            onPress={() => navigation.navigate('TradeDetails', { tradeId })}
          />
        </View>

        <View style={styles.setupCard}>
          <Text style={styles.sectionTitle}>Trade Setup</Text>
          <SetupRow label="Entry Price" value={analysis.analysis15m.entry} />
          <SetupRow
            label="Stop Loss"
            value={analysis.analysis15m.stopLoss}
            valueColor={colors.danger}
          />
          <SetupRow
            label="Take Profit"
            value={analysis.analysis15m.takeProfit}
            valueColor={colors.success}
          />

          <View style={styles.metrics}>
            <Metric
              label="Risk:Reward"
              value={analysis.analysis15m.riskReward || '—'}
            />
            <Metric
              label="Potential"
              value={estimatePips(
                analysis.analysis15m.entry,
                analysis.analysis15m.takeProfit,
              )}
            />
            <Metric
              label="Quality"
              value={qualityFromConfidence(analysis.confidence)}
            />
          </View>
        </View>

        {analysis.explanation || analysis.finalDecision ? (
          <View style={styles.explainBox}>
            <Text style={styles.explainLabel}>Explanation</Text>
            <Text style={styles.explainText}>
              {analysis.explanation || analysis.finalDecision}
            </Text>
          </View>
        ) : null}

        {analysis.warnings && analysis.warnings.length > 0 ? (
          <View style={styles.warnBox}>
            <Text style={styles.warnLabel}>Warnings</Text>
            {analysis.warnings.map((w) => (
              <Text key={w} style={styles.warnText}>
                • {w}
              </Text>
            ))}
          </View>
        ) : null}

        <GradientButton
          label="View Detailed Analysis"
          onPress={() => navigation.replace('TradeDetails', { tradeId })}
        />
        <Pressable
          style={styles.secondaryLink}
          onPress={() => navigation.navigate('MainTabs')}
        >
          <Text style={styles.secondaryLinkText}>New Scan</Text>
        </Pressable>
      </ScrollView>
    </ScreenContainer>
  );
}

function TfCard({
  tf,
  label,
  color,
  confidence,
  onPress,
}: {
  tf: string;
  label: string;
  color: string;
  confidence: number;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.tfCard} onPress={onPress}>
      <Text style={styles.tfName}>{tf}</Text>
      <Text style={[styles.tfBias, { color }]} numberOfLines={1}>
        {label}
      </Text>
      <Text style={styles.tfConf}>{Math.round(confidence)}%</Text>
    </Pressable>
  );
}

function SetupRow({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={styles.setupRow}>
      <Text style={styles.setupLabel}>{label}</Text>
      <Text style={[styles.setupValue, valueColor ? { color: valueColor } : null]}>
        {value}
      </Text>
    </View>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingTop: 8,
    paddingBottom: 36,
    gap: 14,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  heading: {
    color: colors.textMuted,
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
  },
  pair: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 26,
    marginTop: 2,
  },
  hero: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 20,
    padding: 18,
    gap: 8,
  },
  biasLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
  },
  biasValue: {
    fontFamily: fonts.display,
    fontSize: 36,
    letterSpacing: 1,
    marginBottom: 4,
  },
  sectionTitle: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 16,
  },
  tfRow: {
    flexDirection: 'row',
    gap: 10,
  },
  tfCard: {
    flex: 1,
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    gap: 4,
  },
  tfName: {
    color: colors.textMuted,
    fontFamily: fonts.bodyMedium,
    fontSize: 11,
  },
  tfBias: {
    fontFamily: fonts.bodyBold,
    fontSize: 12,
  },
  tfConf: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 11,
  },
  setupCard: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    gap: 12,
  },
  setupRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  setupLabel: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 14,
  },
  setupValue: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 15,
  },
  metrics: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  metric: {
    flex: 1,
    backgroundColor: colors.surfaceElevated,
    borderRadius: 12,
    padding: 10,
  },
  metricLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 10,
    marginBottom: 4,
  },
  metricValue: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 13,
  },
  explainBox: {
    backgroundColor: colors.surfaceElevated,
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  explainLabel: {
    color: colors.primary,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
    marginBottom: 6,
  },
  explainText: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 14,
    lineHeight: 21,
  },
  warnBox: {
    backgroundColor: colors.warningDim,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: 'rgba(245, 185, 66, 0.35)',
  },
  warnLabel: {
    color: colors.warning,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
    marginBottom: 6,
  },
  warnText: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 19,
  },
  secondaryLink: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  secondaryLinkText: {
    color: colors.textSecondary,
    fontFamily: fonts.bodyMedium,
    fontSize: 14,
  },
});
