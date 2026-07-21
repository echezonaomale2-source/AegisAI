import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import type { TradeRecord } from '../types/analysis';
import { BiasBadge } from './BiasBadge';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';
import { formatTimestamp, outcomeLabel } from '../utils/formatters';

interface HistoryItemProps {
  trade: TradeRecord;
  onPress: () => void;
}

function outcomeStyle(trade: TradeRecord) {
  if (trade.outcome === 'TAKE_PROFIT') {
    return { color: colors.success, label: 'TP Hit' };
  }
  if (trade.outcome === 'STOP_LOSS') {
    return { color: colors.danger, label: 'SL Hit' };
  }
  return { color: colors.warning, label: outcomeLabel(trade.outcome) };
}

export function HistoryItem({ trade, onPress }: HistoryItemProps) {
  const outcome = outcomeStyle(trade);

  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.top}>
        <View style={styles.left}>
          <View style={styles.pairRow}>
            <Text style={styles.pair}>{trade.pair}</Text>
            <BiasBadge bias={trade.bias} size="sm" />
          </View>
          <Text style={styles.time}>{formatTimestamp(trade.createdAt)}</Text>
        </View>
        <Image
          source={{ uri: trade.chart15mUri }}
          style={styles.thumb}
          resizeMode="cover"
        />
      </View>

      <View style={styles.meta}>
        <View style={styles.metaItem}>
          <Text style={styles.metaLabel}>Entry</Text>
          <Text style={styles.metaValue}>{trade.entry}</Text>
        </View>
        <View style={styles.metaItem}>
          <Text style={styles.metaLabel}>R:R</Text>
          <Text style={styles.metaValue}>{trade.riskReward}</Text>
        </View>
        <View style={styles.metaItem}>
          <Text style={styles.metaLabel}>Result</Text>
          <Text style={[styles.metaValue, { color: outcome.color }]}>{outcome.label}</Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
  },
  top: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 14,
    gap: 12,
  },
  left: {
    flex: 1,
  },
  pairRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  pair: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 17,
  },
  time: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
  },
  thumb: {
    width: 64,
    height: 48,
    borderRadius: 8,
    backgroundColor: colors.surfaceElevated,
  },
  meta: {
    flexDirection: 'row',
    gap: 8,
  },
  metaItem: {
    flex: 1,
    backgroundColor: colors.surfaceElevated,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 8,
  },
  metaLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 10,
    marginBottom: 2,
  },
  metaValue: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
  },
});
