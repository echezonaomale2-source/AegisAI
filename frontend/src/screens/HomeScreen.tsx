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

export function HomeScreen({ navigation }: Props) {
  const { uploads, pickImage, allUploaded } = useChartUploads();
  const [pair, setPair] = useState('EURUSD');
  const [editingPair, setEditingPair] = useState(false);

  const onAnalyze = () => {
    if (!uploads.chart4h || !uploads.chart1h || !uploads.chart15m) {
      return;
    }

    navigation.navigate('Analyzing', {
      chart4hUri: uploads.chart4h,
      chart1hUri: uploads.chart1h,
      chart15mUri: uploads.chart15m,
      pair: pair.trim() || 'UNKNOWN',
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

        <ChartUploadCard
          title="Higher Timeframe (4H)"
          subtitle="Market structure & bias"
          uploadLabel="Upload 4H Chart"
          imageUri={uploads.chart4h}
          onChoose={() => void pickImage('chart4h')}
          onReplace={() => void pickImage('chart4h')}
        />
        <ChartUploadCard
          title="Middle Timeframe (1H)"
          subtitle="Confirmation & liquidity"
          uploadLabel="Upload 1H Chart"
          imageUri={uploads.chart1h}
          onChoose={() => void pickImage('chart1h')}
          onReplace={() => void pickImage('chart1h')}
        />
        <ChartUploadCard
          title="Lower Timeframe (15M)"
          subtitle="Entry refinement"
          uploadLabel="Upload 15M Chart"
          imageUri={uploads.chart15m}
          onChoose={() => void pickImage('chart15m')}
          onReplace={() => void pickImage('chart15m')}
        />

        <View style={styles.tipBox}>
          <Ionicons name="bulb-outline" size={18} color={colors.success} />
          <Text style={styles.tipText}>
            Use clear, full-chart screenshots. Crop out menus when possible for better vision
            accuracy.
          </Text>
        </View>

        <GradientButton
          label="Analyze Charts"
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
