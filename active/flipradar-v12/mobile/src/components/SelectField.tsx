import React, { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTheme } from "@/theme/ThemeProvider";
import { IconButton } from "./IconButton";

export function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  const { colors, radii, typography } = useTheme();
  const [open, setOpen] = useState(false);
  return (
    <View style={{ gap: 6 }}>
      <Text
        style={[
          typography.caption,
          { color: colors.textMuted, fontWeight: "600" },
        ]}
      >
        {label}
      </Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityValue={{
          text: options.find((option) => option.value === value)?.label,
        }}
        accessibilityState={{ expanded: open }}
        aria-expanded={open}
        onPress={() => setOpen(true)}
        style={{
          minHeight: 44,
          borderWidth: 1,
          borderColor: open ? colors.focus : colors.border,
          borderRadius: radii.md,
          backgroundColor: colors.surface,
          paddingHorizontal: 12,
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <Text
          numberOfLines={1}
          style={[typography.body, { color: colors.text, flex: 1 }]}
        >
          {options.find((option) => option.value === value)?.label ?? "Wybierz"}
        </Text>
        <Ionicons name="chevron-down" size={15} color={colors.textMuted} />
      </Pressable>
      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={() => setOpen(false)}
      >
        <Pressable
          accessibilityLabel="Zamknij wybór"
          accessibilityRole="button"
          onPress={() => setOpen(false)}
          style={{
            flex: 1,
            backgroundColor: colors.overlay,
            justifyContent: "center",
            padding: 24,
          }}
        >
          <Pressable
            accessibilityViewIsModal
            onPress={(event) => event.stopPropagation()}
            style={{
              backgroundColor: colors.surface,
              borderRadius: radii.xl,
              padding: 20,
              width: "100%",
              maxWidth: 440,
              maxHeight: "80%",
              alignSelf: "center",
              borderWidth: 1,
              borderColor: colors.border,
            }}
          >
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 12,
              }}
            >
              <Text style={[typography.headline, { color: colors.text }]}>
                {label}
              </Text>
              <IconButton
                icon="close-outline"
                label="Zamknij wybór"
                onPress={() => setOpen(false)}
              />
            </View>
            <ScrollView keyboardShouldPersistTaps="handled">
              {options.map((option) => (
                <Pressable
                  key={option.value}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: option.value === value }}
                  onPress={() => {
                    onChange(option.value);
                    setOpen(false);
                  }}
                  style={{
                    minHeight: 48,
                    flexDirection: "row",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingHorizontal: 12,
                    borderRadius: radii.md,
                    backgroundColor:
                      option.value === value ? colors.accentBg : "transparent",
                  }}
                >
                  <Text style={[typography.body, { color: colors.text }]}>
                    {option.label}
                  </Text>
                  {option.value === value ? (
                    <Ionicons
                      name="checkmark"
                      size={18}
                      color={colors.accent}
                    />
                  ) : null}
                </Pressable>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}
