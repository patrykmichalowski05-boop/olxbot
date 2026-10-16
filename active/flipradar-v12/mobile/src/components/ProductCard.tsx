import React from "react";
import { View } from "react-native";
import { OfferRow, type OfferRowProps } from "@/features/workspace/OfferRow";
import { useTheme } from "@/theme/ThemeProvider";

export function ProductCard(props: OfferRowProps) {
  const { colors, radii } = useTheme();
  return (
    <View
      style={{
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.xl,
        overflow: "hidden",
      }}
    >
      <OfferRow {...props} last />
    </View>
  );
}
