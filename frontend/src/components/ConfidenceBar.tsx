import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';
import { formatConfidence } from '../utils/formatters';

interface ConfidenceBarProps {
  value: number;
  label?: string;
  color?: string;
}

export function ConfidenceBar({
  value,
  label = 'Confidence',
  color = colors.success,
}: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <Text style={styles.label}>{label}</Text>
        <Text style={[styles.value, { color }]}>{formatConfidence(clamped)}</Text>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${clamped}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 8,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  label: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 13,
  },
  value: {
    fontFamily: fonts.bodyBold,
    fontSize: 13,
  },
  track: {
    height: 8,
    borderRadius: 999,
    backgroundColor: colors.surfaceElevated,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 999,
  },
});
