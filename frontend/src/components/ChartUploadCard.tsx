import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { fonts } from '../theme/typography';

interface ChartUploadCardProps {
  title: string;
  subtitle: string;
  uploadLabel: string;
  imageUri: string | null;
  onChoose: () => void;
  onReplace: () => void;
}

export function ChartUploadCard({
  title,
  subtitle,
  uploadLabel,
  imageUri,
  onChoose,
  onReplace,
}: ChartUploadCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
        {imageUri ? (
          <View style={styles.readyBadge}>
            <Ionicons name="checkmark-circle" size={18} color={colors.success} />
          </View>
        ) : null}
      </View>

      {imageUri ? (
        <View style={styles.previewRow}>
          <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="cover" />
          <Pressable style={styles.replaceButton} onPress={onReplace}>
            <Ionicons name="cloud-upload-outline" size={16} color={colors.primary} />
            <Text style={styles.replaceText}>Replace</Text>
          </Pressable>
        </View>
      ) : (
        <Pressable style={styles.uploadArea} onPress={onChoose}>
          <View style={styles.uploadIcon}>
            <Ionicons name="cloud-upload-outline" size={22} color={colors.primary} />
          </View>
          <Text style={styles.uploadTitle}>{uploadLabel}</Text>
          <Text style={styles.uploadHint}>PNG · JPG · JPEG</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderColor: colors.surfaceBorder,
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  headerText: {
    flex: 1,
    paddingRight: 8,
  },
  title: {
    color: colors.text,
    fontFamily: fonts.displayMedium,
    fontSize: 16,
  },
  subtitle: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
    marginTop: 3,
  },
  readyBadge: {
    marginTop: 2,
  },
  uploadArea: {
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: 'rgba(124, 92, 255, 0.45)',
    borderRadius: 14,
    backgroundColor: colors.primaryDim,
    minHeight: 96,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 16,
  },
  uploadIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(124, 92, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  uploadTitle: {
    color: colors.text,
    fontFamily: fonts.bodyBold,
    fontSize: 14,
  },
  uploadHint: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 11,
  },
  previewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  preview: {
    width: 88,
    height: 64,
    borderRadius: 10,
    backgroundColor: colors.surfaceElevated,
  },
  replaceButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: colors.primaryDim,
  },
  replaceText: {
    color: colors.primary,
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
  },
});
