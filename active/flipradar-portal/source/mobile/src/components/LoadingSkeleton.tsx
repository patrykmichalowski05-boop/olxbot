import React, { useEffect, useState } from 'react';
import { AccessibilityInfo, Animated, StyleSheet, View } from 'react-native';
import { useTheme } from '@/theme/ThemeProvider';

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  const { colors, radii, spacing } = useTheme();
  const [opacity] = useState(() => new Animated.Value(0.65));
  const [reduceMotion, setReduceMotion] = useState(true);
  useEffect(() => {
    let alive = true;
    void AccessibilityInfo.isReduceMotionEnabled()
      .then((value) => {
        if (alive) setReduceMotion(value);
      })
      .catch(() => undefined);
    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setReduceMotion,
    );
    return () => {
      alive = false;
      subscription.remove();
    };
  }, []);
  useEffect(() => {
    if (reduceMotion) {
      opacity.setValue(0.65);
      return;
    }
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.35, duration: 850, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.8, duration: 850, useNativeDriver: true }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [opacity, reduceMotion]);
  const line = { backgroundColor: colors.surfaceElevated, borderRadius: radii.sm };
  return (
    <View
      accessibilityLabel="Ładowanie ofert"
      accessibilityState={{ busy: true }}
      aria-busy
      style={{ gap: spacing.md }}
    >
      {Array.from({ length: rows }, (_, index) => (
        <View
          key={index}
          style={{
            backgroundColor: colors.surface,
            borderRadius: radii.xxl,
            borderWidth: 1,
            borderColor: colors.border,
            padding: spacing.lg,
          }}
        >
          <Animated.View style={{ opacity, gap: spacing.lg }}>
            <View style={styles.row}>
              <View style={[line, { width: 72, height: 72, borderRadius: radii.lg }]} />
              <View style={{ flex: 1, gap: spacing.sm }}>
                <View style={[line, { width: 54, height: 18 }]} />
                <View style={[line, { width: '92%', height: 14 }]} />
                <View style={[line, { width: '65%', height: 14 }]} />
              </View>
            </View>
            <View style={styles.row}>
              {[0, 1, 2].map((key) => (
                <View key={key} style={[line, { flex: 1, height: 44 }]} />
              ))}
            </View>
            <View style={[line, { width: '100%', height: 32 }]} />
          </Animated.View>
        </View>
      ))}
    </View>
  );
}
const styles = StyleSheet.create({ row: { flexDirection: 'row', gap: 12 } });
