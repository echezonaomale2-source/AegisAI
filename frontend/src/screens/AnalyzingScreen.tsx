import React, { useEffect, useRef, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LoadingStages, ANALYSIS_STAGES } from '../components/LoadingStages';
import { ScreenContainer } from '../components/ScreenContainer';
import type { RootStackParamList } from '../navigation/types';
import { analyzeCharts } from '../services/api';
import { persistChartImage } from '../storage/imageStorage';
import { insertTrade } from '../storage/tradeRepository';
import type { TradeRecord } from '../types/analysis';
import { createId } from '../utils/formatters';

type Props = NativeStackScreenProps<RootStackParamList, 'Analyzing'>;

const STAGE_INTERVAL_MS = 900;

export function AnalyzingScreen({ navigation, route }: Props) {
  const { chart4hUri, chart1hUri, chart15mUri, pair } = route.params;
  const [stageIndex, setStageIndex] = useState(0);
  const startedRef = useRef(false);

  useEffect(() => {
    const stageTimer = setInterval(() => {
      setStageIndex((prev) => Math.min(prev + 1, ANALYSIS_STAGES.length - 1));
    }, STAGE_INTERVAL_MS);

    return () => clearInterval(stageTimer);
  }, []);

  useEffect(() => {
    if (startedRef.current) {
      return;
    }
    startedRef.current = true;

    const run = async () => {
      try {
        const analysis = await analyzeCharts({
          pair,
          chart4hUri,
          chart1hUri,
          chart15mUri,
        });

        const tradeId = analysis.tradeId || createId();
        const now = new Date().toISOString();

        const [saved4h, saved1h, saved15m] = await Promise.all([
          persistChartImage(chart4hUri, tradeId, '4h'),
          persistChartImage(chart1hUri, tradeId, '1h'),
          persistChartImage(chart15mUri, tradeId, '15m'),
        ]);

        const trade: TradeRecord = {
          id: tradeId,
          createdAt: now,
          updatedAt: now,
          pair: analysis.pair,
          bias: analysis.bias,
          confidence: analysis.confidence,
          entry: analysis.analysis15m.entry,
          stopLoss: analysis.analysis15m.stopLoss,
          takeProfit: analysis.analysis15m.takeProfit,
          riskReward: analysis.analysis15m.riskReward,
          chart4hUri: saved4h,
          chart1hUri: saved1h,
          chart15mUri: saved15m,
          outcomeChartUri: null,
          outcome: null,
          analysisJson: JSON.stringify(analysis),
          finalDecision: analysis.finalDecision,
          status: 'WAITING',
        };

        await insertTrade(trade);

        // Allow the final stage animation to register before navigating.
        setStageIndex(ANALYSIS_STAGES.length - 1);
        setTimeout(() => {
          navigation.replace('Results', { tradeId, analysis });
        }, 500);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Unable to complete analysis.';
        Alert.alert('Analysis failed', message, [
          { text: 'Back', onPress: () => navigation.goBack() },
        ]);
      }
    };

    void run();
  }, [chart15mUri, chart1hUri, chart4hUri, navigation, pair]);

  return (
    <ScreenContainer>
      <View style={styles.wrap}>
        <LoadingStages stageIndex={stageIndex} />
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: 'center',
  },
});
