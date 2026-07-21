import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import type { MainTabParamList, RootStackParamList } from '../navigation/types';
import { fetchEvaluationDashboard, fetchResearchDashboard, type EvaluationDashboard, type ResearchDashboard } from '../services/api';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, 'Insights'>,
  NativeStackScreenProps<RootStackParamList>
>;

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

export function ResearchScreen({ navigation }: Props) {
  const [data, setData] = useState<ResearchDashboard | null>(null);
  const [evalData, setEvalData] = useState<EvaluationDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [research, evaluation] = await Promise.all([
        fetchResearchDashboard(),
        fetchEvaluationDashboard(),
      ]);
      setData(research);
      setEvalData(evaluation);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load research dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const cal = data?.current_confidence_calibration;
  const most = data?.most_reliable_feature_combination;
  const least = data?.least_reliable_feature_combination;

  return (
    <ScreenContainer edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={styles.title}>Insights</Text>
        <Text style={styles.subtitle}>Analysis quality · calibration · patterns</Text>
      </View>

      {loading && !data ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.primary} />
          }
        >
          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Section title="Overall System Health">
            <Text style={styles.body}>
              {evalData?.overall_system_health
                ? `${evalData.overall_system_health.overall_grade} · ${evalData.overall_system_health.overall_score.toFixed(1)}`
                : '—'}
            </Text>
            {(evalData?.overall_system_health?.modules ?? []).map((m) => (
              <Text key={m.module} style={styles.muted}>
                {m.module}: {m.grade} ({m.score.toFixed(0)})
              </Text>
            ))}
            <Text style={styles.muted}>
              Calibration: {evalData?.current_calibration_quality ?? '—'} · Path logs:{' '}
              {evalData?.decision_path_log_count ?? 0}
            </Text>
          </Section>

          <View style={styles.row}>
            <Stat label="Total Analyses" value={String(data?.total_analyses ?? 0)} />
            <Stat label="Awaiting Results" value={String(data?.trades_awaiting_results ?? 0)} />
            <Stat label="Completed Reviews" value={String(data?.completed_reviews ?? 0)} />
          </View>

          <Section title="Confidence Calibration">
            <Text style={styles.body}>
              Gap {cal?.global_gap?.toFixed?.(1) ?? '0'}% · Factor {cal?.adjustment_factor ?? 1} · Samples{' '}
              {cal?.sample_count ?? 0}
            </Text>
            {(cal?.notes ?? []).map((n) => (
              <Text key={n} style={styles.muted}>
                {n}
              </Text>
            ))}
            {(cal?.bins ?? []).length > 0 ? (
              <View style={styles.binBlock}>
                {(cal?.bins ?? []).map((b) => (
                  <Text key={b.bin_label} style={styles.muted}>
                    {b.bin_label}: {b.predictions} preds · realized{' '}
                    {b.realized_rate != null ? `${b.realized_rate.toFixed(0)}%` : '—'}
                    {b.calibration_gap != null ? ` · gap ${b.calibration_gap.toFixed(0)}%` : ''}
                  </Text>
                ))}
              </View>
            ) : null}
          </Section>

          <Section title="Memory Snapshot">
            <Text style={styles.body}>
              WR {data?.memory_snapshot?.estimated_win_rate ?? '—'}% · Wins{' '}
              {data?.memory_snapshot?.winning_trades ?? 0} · Losses{' '}
              {data?.memory_snapshot?.losing_trades ?? 0} · Waiting{' '}
              {data?.memory_snapshot?.waiting_trades ?? 0}
            </Text>
            <Text style={styles.muted}>
              Best pair: {data?.memory_snapshot?.most_successful_pair ?? '—'} · Last learn:{' '}
              {data?.memory_snapshot?.last_learning_update ?? 'never'}
            </Text>
          </Section>

          <Section title="Pattern Statistics">
            {(data?.top_patterns ?? []).length === 0 ? (
              <Text style={styles.muted}>No pattern samples yet.</Text>
            ) : (
              (data?.top_patterns ?? []).map((p) => (
                <Text key={p.pattern_id} style={styles.muted}>
                  {(p.feature_combination ?? []).join(' + ') || p.pattern_id}: WR{' '}
                  {p.reliability_score ?? '—'}% · {p.occurrences} occ · {p.wins}W/{p.losses}L
                </Text>
              ))
            )}
          </Section>

          <Section title="Most Reliable Feature Combination">
            <Text style={styles.body}>
              {most
                ? `${most.feature_combination?.join(' + ') || most.pattern_id} · reliability ${most.reliability_score ?? '—'}% · ${most.occurrences} occ`
                : 'Not enough closed pattern samples yet.'}
            </Text>
          </Section>

          <Section title="Least Reliable Feature Combination">
            <Text style={styles.body}>
              {least
                ? `${least.feature_combination?.join(' + ') || least.pattern_id} · reliability ${least.reliability_score ?? '—'}% · ${least.occurrences} occ`
                : 'Not enough closed pattern samples yet.'}
            </Text>
          </Section>

          <Section title="Feature Reliability">
            {(data?.learning_snapshot?.feature_reliability ?? []).length === 0 ? (
              <Text style={styles.muted}>No feature reliability samples yet.</Text>
            ) : (
              (data?.learning_snapshot?.feature_reliability ?? []).map((f) => (
                <Text key={f.feature} style={styles.muted}>
                  {f.feature}: WR {f.win_rate ?? '—'}% · {f.wins}W/{f.losses}L ({f.total})
                </Text>
              ))
            )}
          </Section>

          <Section title="Most Common Losing Reason">
            <Text style={styles.body}>{data?.most_common_reason_for_losing_trades ?? '—'}</Text>
          </Section>

          <Section title="Most Common NO TRADE Reason">
            <Text style={styles.body}>{data?.most_common_reason_for_no_trade ?? '—'}</Text>
          </Section>

          <Section title="Recent Lessons">
            {(data?.recent_lessons ?? []).length === 0 ? (
              <Text style={styles.muted}>No lessons stored yet.</Text>
            ) : (
              (data?.recent_lessons ?? []).map((lesson, i) => (
                <Text key={`${i}-${lesson.slice(0, 24)}`} style={styles.lesson}>
                  · {lesson}
                </Text>
              ))
            )}
          </Section>

          {data?.decision_quality_distribution &&
          Object.keys(data.decision_quality_distribution).length > 0 ? (
            <Section title="Decision Quality Distribution">
              {Object.entries(data.decision_quality_distribution).map(([k, v]) => (
                <Text key={k} style={styles.muted}>
                  {k}: {v}
                </Text>
              ))}
            </Section>
          ) : null}

          <PrimaryButton label="AI Memory" onPress={() => navigation.navigate('Memory')} mode="outlined" />
          <PrimaryButton
            label="History"
            onPress={() => navigation.navigate('History')}
            mode="outlined"
            color={colors.secondary}
          />
        </ScrollView>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: { paddingTop: 8, paddingBottom: 12 },
  title: { color: colors.text, fontFamily: fonts.display, fontSize: 28 },
  subtitle: { color: colors.textSecondary, marginTop: 4, fontFamily: fonts.body, fontSize: 14 },
  content: { paddingBottom: 40, gap: 14 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  error: { color: colors.danger, marginBottom: 8, fontFamily: fonts.body },
  row: { flexDirection: 'row', gap: 10 },
  stat: {
    flex: 1,
    backgroundColor: colors.surfaceElevated,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  statValue: { color: colors.primary, fontFamily: fonts.display, fontSize: 22 },
  statLabel: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 11, marginTop: 4 },
  section: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    gap: 6,
  },
  sectionTitle: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 15,
    marginBottom: 4,
  },
  body: { color: colors.textSecondary, fontFamily: fonts.body, fontSize: 14, lineHeight: 20 },
  muted: { color: colors.textMuted, fontFamily: fonts.body, fontSize: 13, lineHeight: 18 },
  lesson: { color: colors.textSecondary, fontFamily: fonts.body, fontSize: 13, lineHeight: 19 },
  binBlock: { marginTop: 4, gap: 2 },
});
