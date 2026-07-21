import React, { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

export const ANALYSIS_STAGES = [
  'Reading 4H Chart',
  'Reading 1H Chart',
  'Reading 15M Chart',
  'Analyzing market structure',
  'Detecting liquidity & order blocks',
  'Generating AI insight',
  'Preparing trading plan',
] as const;

interface LoadingStagesProps {
  stageIndex: number;
}

export function LoadingStages({ stageIndex }: LoadingStagesProps) {
  const spin = useSharedValue(0);
  const pulse = useSharedValue(0.85);

  useEffect(() => {
    spin.value = withRepeat(
      withTiming(360, { duration: 2400, easing: Easing.linear }),
      -1,
      false,
    );
    pulse.value = withRepeat(
      withTiming(1, { duration: 1100, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [pulse, spin]);

  const ringStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${spin.value}deg` }, { scale: pulse.value }],
  }));

  return (
    <View style={styles.wrap}>
      <View style={styles.ringWrap}>
        <Animated.View style={[styles.ring, ringStyle]} />
        <View style={styles.ringInner}>
          <Ionicons name="analytics-outline" size={32} color={colors.success} />
        </View>
      </View>

      <Text style={styles.title}>Analyzing...</Text>
      <Text style={styles.subtitle}>Please wait</Text>

      <View style={styles.list}>
        {ANALYSIS_STAGES.map((stage, index) => {
          const done = index < stageIndex;
          const active = index === stageIndex;
          return (
            <View key={stage} style={styles.item}>
              {done ? (
                <Ionicons name="checkmark-circle" size={20} color={colors.success} />
              ) : (
                <View style={[styles.circle, active && styles.circleActive]} />
              )}
              <Text
                style={[
                  styles.itemText,
                  done && styles.itemDone,
                  active && styles.itemActive,
                ]}
              >
                {stage}
              </Text>
            </View>
          );
        })}
      </View>

      <View style={styles.footer}>
        <Ionicons name="hardware-chip-outline" size={18} color={colors.primary} />
        <Text style={styles.footerText}>
          AI is analyzing charts with Smart Money Concepts — no indicators.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    paddingVertical: 20,
    paddingHorizontal: 8,
  },
  ringWrap: {
    width: 120,
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 28,
  },
  ring: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 3,
    borderColor: colors.success,
    borderTopColor: 'transparent',
    borderRightColor: 'rgba(46, 229, 157, 0.25)',
  },
  ringInner: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: colors.successDim,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(46, 229, 157, 0.35)',
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 26,
  },
  subtitle: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 15,
    marginTop: 4,
    marginBottom: 28,
  },
  list: {
    width: '100%',
    gap: 14,
    marginBottom: 32,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  circle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: colors.surfaceBorder,
  },
  circleActive: {
    borderColor: colors.success,
    backgroundColor: colors.successDim,
  },
  itemText: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 14,
  },
  itemDone: {
    color: colors.textSecondary,
  },
  itemActive: {
    color: colors.text,
    fontFamily: fonts.bodyMedium,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    paddingHorizontal: 12,
  },
  footerText: {
    flex: 1,
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    lineHeight: 18,
  },
});
