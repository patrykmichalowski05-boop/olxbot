import React from "react";
import { Text, View } from "react-native";
import { IconButton } from "@/components/IconButton";
import { useTheme } from "@/theme/ThemeProvider";

export function WorkspaceNotice({
  text,
  onDismiss,
}: {
  text: string;
  onDismiss?: () => void;
}) {
  const { colors, radii, typography } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
        backgroundColor: colors.accentBg,
        borderRadius: radii.md,
        padding: 12,
      }}
    >
      <Text
        accessibilityLiveRegion="polite"
        style={[typography.body, { color: colors.accent, flex: 1 }]}
      >
        {text}
      </Text>
      {onDismiss ? (
        <IconButton
          label="Zamknij komunikat"
          icon="close-outline"
          onPress={onDismiss}
        />
      ) : null}
    </View>
  );
}
