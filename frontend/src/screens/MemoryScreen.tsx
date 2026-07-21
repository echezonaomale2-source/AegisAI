import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useFocusEffect } from '@react-navigation/native';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import type { RootStackParamList } from '../navigation/types';
import { fetchMemoryStats, type MemoryStats } from '../services/api';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'Memory'>;

export function MemoryScreen({ navigation }: Props) {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMemoryStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load AI Memory.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  return (
    <ScreenContainer>
      <View style={styles.header}>
        <Text style={styles.title}>AI Memory</Text>
        <Text style={styles.subtitle}>Permanent learning archive</Text>
      </View>

      {loading && !stats ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.primary} />
          }
          showsVerticalScrollIndicator={false}
        >
          {error ? <Text style={styles.error}>{error}</Text> : null}

          <StatCard label="Total Trades Stored" value={String(stats?.total_trades_stored ?? 0)} />
          <StatCard label="Winning Trades" value={String(stats?.winning_trades ?? 0)} accent={colors.primary} />
          <StatCard label="Losing Trades" value={String(stats?.losing_trades ?? 0)} accent={colors.danger} />
          <StatCard
            label="Current Estimated Win Rate"
            value={
              stats?.estimated_win_rate != null ? `${stats.estimated_win_rate.toFixed(1)}%` : '—'
            }
          />
          <StatCard label="Most Successful Pair" value={stats?.most_successful_pair ?? '—'} />
          <StatCard
            label="Most Successful Timeframe Alignment"
            value={stats?.most_successful_timeframe_alignment ?? '—'}
          />
          <StatCard
            label="Most Successful Feature Combination"
            value={
              stats?.most_successful_feature_combination
                ? `${stats.most_successful_feature_combination.pattern} (${stats.most_successful_feature_combination.wins} wins)`
                : '—'
            }
          />
          <StatCard
            label="Most Common Losing Pattern"
            value={
              stats?.most_common_losing_pattern
                ? `${stats.most_common_losing_pattern.pattern} (${stats.most_common_losing_pattern.losses} losses)`
                : '—'
            }
          />
          <StatCard
            label="Total Memories Stored"
            value={String(stats?.total_memories_stored ?? 0)}
          />
          <StatCard
            label="Last Learning Update"
            value={stats?.last_learning_update ?? 'never'}
          />

          {stats?.grade_distribution && Object.keys(stats.grade_distribution).length > 0 ? (
            <StatCard
              label="Trade Quality Grades"
              value={Object.entries(stats.grade_distribution)
                .map(([g, n]) => `${g}: ${n}`)
                .join(' · ')}
            />
          ) : null}

          {(stats?.top_patterns ?? []).slice(0, 3).map((pattern) => (
            <StatCard
              key={pattern.pattern}
              label="Pattern Performance"
              value={`${pattern.pattern}\n${pattern.wins}W / ${pattern.losses}L · ${pattern.trades} trades · WR ${pattern.win_rate ?? '—'}%`}
              accent={colors.primary}
            />
          ))}

          <PrimaryButton
            label="Research Dashboard"
            mode="outlined"
            color={colors.primary}
            onPress={() => navigation.navigate('MainTabs', { screen: 'Insights' })}
          />
          <PrimaryButton
            label="History"
            mode="outlined"
            color={colors.secondary}
            onPress={() => navigation.navigate('History')}
          />
          <PrimaryButton
            label="Back to Home"
            mode="text"
            color={colors.textSecondary}
            onPress={() => navigation.navigate('MainTabs')}
          />
        </ScrollView>
      )}
    </ScreenContainer>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={[styles.cardValue, accent ? { color: accent } : null]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 8,
    marginBottom: 12,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.display,
    fontSize: 28,
  },
  subtitle: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 13,
    marginTop: 4,
  },
  content: {
    paddingBottom: 32,
    gap: 10,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  error: {
    color: colors.danger,
    fontFamily: fonts.body,
    marginBottom: 8,
  },
  card: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
  },
  cardLabel: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    marginBottom: 6,
  },
  cardValue: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 16,
    lineHeight: 22,
  },
});
