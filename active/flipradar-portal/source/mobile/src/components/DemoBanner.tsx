import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/AuthContext";
import { getPublicConfig } from "@/api/endpoints/portal";
import { portalEnabled } from "@/utils/config";
import { useTheme } from "@/theme/ThemeProvider";

export function DemoBanner() {
  const { mode } = useAuth();
  const { colors, spacing, typography, radii } = useTheme();
  const config = useQuery({
    queryKey: ["portal-public-config"],
    queryFn: getPublicConfig,
    enabled: mode === "live" && portalEnabled(),
    retry: false,
    staleTime: 60000,
  });

  if (mode !== "demo" && !config.data?.demo_data) {
    return null;
  }

  return (
    <View
      accessibilityRole="text"
      style={[
        styles.banner,
        {
          backgroundColor: colors.accentBg,
          borderColor: colors.accentMuted,
          borderRadius: radii.sm,
          padding: spacing.sm,
          marginBottom: spacing.sm,
        },
      ]}
    >
      <Text
        style={[
          typography.caption,
          { color: colors.accent, fontWeight: "600" },
        ]}
      >
        Tryb demo · Dane przykładowe
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { borderWidth: 1 },
});
