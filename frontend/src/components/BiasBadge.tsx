import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { TradeBias } from '../types/analysis';
import { biasColor } from '../utils/formatters';
import { fonts } from '../theme/typography';

interface BiasBadgeProps {
  bias: TradeBias;
  size?: 'sm' | 'md';
}

export function BiasBadge({ bias, size = 'md' }: BiasBadgeProps) {
  const color = biasColor(bias);
  return (
    <View
      style={[
        styles.badge,
        size === 'sm' && styles.badgeSm,
        { backgroundColor: `${color}22`, borderColor: color },
      ]}
    >
      <Text style={[styles.text, size === 'sm' && styles.textSm, { color }]}>{bias}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 6,
    alignSelf: 'flex-start',
  },
  badgeSm: {
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  text: {
    fontFamily: fonts.bodyBold,
    fontSize: 13,
    letterSpacing: 0.8,
  },
  textSm: {
    fontSize: 11,
  },
});
