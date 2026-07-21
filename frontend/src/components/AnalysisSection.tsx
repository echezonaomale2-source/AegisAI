import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme/colors';

interface AnalysisSectionProps {
  title: string;
  accent?: string;
  rows: Array<{ label: string; value: string }>;
  summary?: string;
  reasons?: string[];
}

export function AnalysisSection({
  title,
  accent = colors.primary,
  rows,
  summary,
  reasons,
}: AnalysisSectionProps) {
  return (
    <View style={styles.section}>
      <View style={[styles.accent, { backgroundColor: accent }]} />
      <Text style={styles.title}>{title}</Text>
      {rows.map((row) => (
        <View key={row.label} style={styles.row}>
          <Text style={styles.label}>{row.label}</Text>
          <Text style={styles.value}>{row.value}</Text>
        </View>
      ))}
      {summary ? (
        <View style={styles.summaryBox}>
          <Text style={styles.summaryLabel}>Summary</Text>
          <Text style={styles.summaryText}>{summary}</Text>
        </View>
      ) : null}
      {reasons && reasons.length > 0 ? (
        <View style={styles.reasonsBox}>
          <Text style={styles.summaryLabel}>Reasons</Text>
          {reasons.map((reason) => (
            <Text key={reason} style={styles.reasonItem}>
              • {reason}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 14,
    overflow: 'hidden',
  },
  accent: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 3,
  },
  title: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 8,
  },
  label: {
    color: colors.textMuted,
    fontSize: 13,
    flexShrink: 0,
  },
  value: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'right',
    flex: 1,
  },
  summaryBox: {
    marginTop: 8,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
  },
  reasonsBox: {
    marginTop: 8,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
    gap: 4,
  },
  summaryLabel: {
    color: colors.secondary,
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 6,
  },
  summaryText: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
  },
  reasonItem: {
    color: colors.textSecondary,
    fontSize: 13,
    lineHeight: 19,
  },
});
