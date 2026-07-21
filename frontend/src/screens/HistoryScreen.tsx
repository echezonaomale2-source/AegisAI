import React, { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { HistoryItem } from '../components/HistoryItem';
import { ScreenContainer } from '../components/ScreenContainer';
import { useTrades } from '../hooks/useTrades';
import type { MainTabParamList, RootStackParamList } from '../navigation/types';
import type { TradeRecord } from '../types/analysis';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

type Props = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, 'History'>,
  NativeStackScreenProps<RootStackParamList>
>;

type FilterKey = 'all' | 'open' | 'won' | 'lost';

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'won', label: 'Won' },
  { key: 'lost', label: 'Lost' },
];

function matchesFilter(trade: TradeRecord, filter: FilterKey): boolean {
  if (filter === 'all') return true;
  if (filter === 'open') return trade.status === 'WAITING' || trade.outcome == null;
  if (filter === 'won') return trade.outcome === 'TAKE_PROFIT';
  if (filter === 'lost') return trade.outcome === 'STOP_LOSS';
  return true;
}

export function HistoryScreen({ navigation }: Props) {
  const { trades, loading, refresh } = useTrades();
  const [filter, setFilter] = useState<FilterKey>('all');

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  const filtered = useMemo(
    () => trades.filter((t) => matchesFilter(t, filter)),
    [trades, filter],
  );

  return (
    <ScreenContainer edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <Text style={styles.title}>History</Text>
        <Text style={styles.subtitle}>Trade archive & outcomes</Text>
      </View>

      <View style={styles.filters}>
        {FILTERS.map((item) => {
          const active = filter === item.key;
          return (
            <Pressable
              key={item.key}
              style={[styles.filterChip, active && styles.filterChipActive]}
              onPress={() => setFilter(item.key)}
            >
              <Text style={[styles.filterText, active && styles.filterTextActive]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyTitle}>No trades here</Text>
              <Text style={styles.emptyText}>
                Scan charts to build your history, then log TP / SL outcomes.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <HistoryItem
              trade={item}
              onPress={() => navigation.navigate('TradeDetails', { tradeId: item.id })}
            />
          )}
        />
      )}

      <Pressable
        style={styles.fab}
        onPress={() => navigation.navigate('Scan')}
        accessibilityLabel="New scan"
      >
        <Ionicons name="add" size={28} color={colors.white} />
      </Pressable>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 8,
    marginBottom: 14,
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
  filters: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 14,
  },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  filterChipActive: {
    backgroundColor: colors.primaryDim,
    borderColor: colors.primary,
  },
  filterText: {
    color: colors.textMuted,
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
  },
  filterTextActive: {
    color: colors.primary,
  },
  list: {
    paddingBottom: 88,
    flexGrow: 1,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  empty: {
    paddingVertical: 48,
    alignItems: 'center',
  },
  emptyTitle: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 16,
    marginBottom: 6,
  },
  emptyText: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 19,
    paddingHorizontal: 24,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.primary,
    shadowOpacity: 0.45,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
});
