import React, { useState } from 'react';
import {
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
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ChartUploadCard } from '../components/ChartUploadCard';
import { GradientButton } from '../components/GradientButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { useChartUploads } from '../hooks/useChartUploads';
import type { MainTabParamList, RootStackParamList } from '../navigation/types';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, 'Scan'>,
  NativeStackScreenProps<RootStackParamList>
>;

const TIMEFRAME_OPTIONS = ['1M', '5M', '15M', '30M', '1H', '4H', '1D', '1W'] as const;

function TimeframePicker({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <View style={styles.tfBlock}>
      <Text style={styles.tfLabel}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tfRow}>
        {TIMEFRAME_OPTIONS.map((option) => {
          const selected = option === value;
          return (
            <Pressable
              key={`${label}-${option}`}
              onPress={() => onChange(option)}
              style={[styles.tfChip, selected && styles.tfChipSelected]}
            >
              <Text style={[styles.tfChipText, selected && styles.tfChipTextSelected]}>{option}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function HomeScreen({ navigation }: Props) {
  const { uploads, pickImage, allUploaded } = useChartUploads();
  const [pair, setPair] = useState('EURUSD');
  const [editingPair, setEditingPair] = useState(false);
  const [timeframeHtf, setTimeframeHtf] = useState('4H');
  const [timeframeMtf, setTimeframeMtf] = useState('1H');
  const [timeframeLtf, setTimeframeLtf] = useState('15M');

  const onAnalyze = () => {
    if (!uploads.chart4h || !uploads.chart1h || !uploads.chart15m) {
      return;
    }

    navigation.navigate('Analyzing', {
      chart4hUri: uploads.chart4h,
      chart1hUri: uploads.chart1h,
      chart15mUri: uploads.chart15m,
      pair: pair.trim() || 'EURUSD',
      timeframeHtf,
      timeframeMtf,
      timeframeLtf,
    });
  };

  return (
    <ScreenContainer edges={['top', 'left', 'right']}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Scan Charts</Text>
          <Pressable hitSlop={12}>
            <Ionicons name="help-circle-outline" size={24} color={colors.textSecondary} />
          </Pressable>
        </View>

        <View style={styles.pairCard}>
          <View style={styles.pairLeft}>
            <View style={styles.flagStack}>
              <View style={[styles.flag, styles.flagA]} />
              <View style={[styles.flag, styles.flagB]} />
            </View>
            {editingPair ? (
              <TextInput
                value={pair}
                onChangeText={setPair}
                onBlur={() => setEditingPair(false)}
                autoFocus
                autoCapitalize="characters"
                placeholderTextColor={colors.textMuted}
                style={styles.pairInput}
              />
            ) : (
              <Text style={styles.pairName}>{pair}</Text>
            )}
          </View>
          <Pressable style={styles.changeBtn} onPress={() => setEditingPair(true)}>
            <Text style={styles.changeText}>Change</Text>
          </Pressable>
        </View>

        <View style={styles.selectionCard}>
          <Text style={styles.sectionTitle}>Timeframes</Text>
          <Text style={styles.sectionHint}>
            Select pair and timeframes first. Charts are analyzed with these labels only — nothing
            is read from the image text.
          </Text>
          <TimeframePicker label="Higher timeframe" value={timeframeHtf} onChange={setTimeframeHtf} />
          <TimeframePicker label="Middle timeframe" value={timeframeMtf} onChange={setTimeframeMtf} />
          <TimeframePicker label="Entry timeframe" value={timeframeLtf} onChange={setTimeframeLtf} />
        </View>

        <ChartUploadCard
          title={`Higher Timeframe (${timeframeHtf})`}
          subtitle="Trend, liquidity, premium/discount, OB, BOS, CHOCH, FVG"
          uploadLabel={`Upload ${timeframeHtf} Chart`}
          imageUri={uploads.chart4h}
          onChoose={() => void pickImage('chart4h')}
          onReplace={() => void pickImage('chart4h')}
        />
        <ChartUploadCard
          title={`Middle Timeframe (${timeframeMtf})`}
          subtitle="HTF alignment, internal structure, mitigation, entry zone"
          uploadLabel={`Upload ${timeframeMtf} Chart`}
          imageUri={uploads.chart1h}
          onChoose={() => void pickImage('chart1h')}
          onReplace={() => void pickImage('chart1h')}
        />
        <ChartUploadCard
          title={`Entry Timeframe (${timeframeLtf})`}
          subtitle="Sweep, trigger, confirmation, precise SL / TP"
          uploadLabel={`Upload ${timeframeLtf} Chart`}
          imageUri={uploads.chart15m}
          onChoose={() => void pickImage('chart15m')}
          onReplace={() => void pickImage('chart15m')}
        />

        <View style={styles.tipBox}>
          <Ionicons name="bulb-outline" size={18} color={colors.success} />
          <Text style={styles.tipText}>
            Use clear, full-chart screenshots that match the selected timeframes. Pair and TF come
            from your selection above.
          </Text>
        </View>

        <GradientButton
          label="Analyze"
          onPress={onAnalyze}
          disabled={!allUploaded}
          style={styles.cta}
        />
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingTop: 8,
    paddingBottom: 28,
    gap: 14,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 28,
  },
  pairCard: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  pairLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  flagStack: {
    width: 36,
    height: 28,
  },
  flag: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.card,
    position: 'absolute',
  },
  flagA: {
    backgroundColor: '#3B82F6',
    left: 0,
    top: 2,
  },
  flagB: {
    backgroundColor: '#EF4444',
    left: 12,
    top: 2,
  },
  pairName: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 18,
  },
  pairInput: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 18,
    flex: 1,
    padding: 0,
  },
  changeBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: colors.primaryDim,
  },
  changeText: {
    color: colors.primary,
    fontFamily: fonts.bodyBold,
    fontSize: 13,
  },
  selectionCard: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    gap: 12,
  },
  sectionTitle: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 16,
  },
  sectionHint: {
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 18,
  },
  tfBlock: {
    gap: 8,
  },
  tfLabel: {
    color: colors.textSecondary,
    fontFamily: fonts.bodyBold,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  tfRow: {
    gap: 8,
  },
  tfChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    backgroundColor: colors.background,
  },
  tfChipSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primaryDim,
  },
  tfChipText: {
    color: colors.textSecondary,
    fontFamily: fonts.bodyBold,
    fontSize: 13,
  },
  tfChipTextSelected: {
    color: colors.primary,
  },
  tipBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: colors.tipBg,
    borderColor: colors.tipBorder,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
  },
  tipText: {
    flex: 1,
    color: colors.textSecondary,
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 19,
  },
  cta: {
    marginTop: 4,
  },
});
