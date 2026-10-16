import React, { useEffect, useState } from "react";
import {
  Keyboard,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { Tabs } from "expo-router";

import { useTheme } from "@/theme/ThemeProvider";
import type { IconName } from "./IconButton";
import { useWorkspaceLayout } from "@/features/workspace/layout";

type BottomTabBarProps = Parameters<
  NonNullable<React.ComponentProps<typeof Tabs>["tabBar"]>
>[0];

const icons: Record<string, [IconName, IconName]> = {
  "radar/index": ["radio-outline", "radio"],
  "watched/index": ["bookmark-outline", "bookmark"],
  "analyze/index": ["scan-outline", "scan"],
  "flips/index": ["briefcase-outline", "briefcase"],
  "settings/index": ["settings-outline", "settings"],
};

export function PremiumTabBar({
  state,
  descriptors,
  navigation,
  insets,
}: BottomTabBarProps) {
  const { colors, radii, typography } = useTheme();
  const { desktop } = useWorkspaceLayout();
  const [keyboardVisible, setKeyboardVisible] = useState(false);
  useEffect(() => {
    const show = Keyboard.addListener("keyboardDidShow", () =>
      setKeyboardVisible(true),
    );
    const hide = Keyboard.addListener("keyboardDidHide", () =>
      setKeyboardVisible(false),
    );
    return () => {
      show.remove();
      hide.remove();
    };
  }, []);
  const activeOptions = descriptors[state.routes[state.index].key].options;
  if (Platform.OS === "web" || desktop) return null;
  if (keyboardVisible && activeOptions.tabBarHideOnKeyboard) return null;
  return (
    <View
      style={{
        paddingHorizontal: 12,
        paddingTop: 8,
        paddingBottom: Math.max(insets.bottom, 12),
        backgroundColor: colors.background,
      }}
    >
      <View
        style={[
          styles.bar,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
            borderRadius: radii.xxl,
          },
        ]}
      >
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          const options = descriptors[route.key].options;
          const label = options.title ?? route.name;
          const icon =
            icons[route.name]?.[focused ? 1 : 0] ?? "ellipse-outline";
          return (
            <Pressable
              key={route.key}
              accessibilityRole={Platform.OS === "web" ? "tab" : "button"}
              accessibilityLabel={options.tabBarAccessibilityLabel ?? label}
              accessibilityState={{ selected: focused }}
              aria-selected={focused}
              onPress={() => {
                const event = navigation.emit({
                  type: "tabPress",
                  target: route.key,
                  canPreventDefault: true,
                });
                if (!focused && !event.defaultPrevented)
                  navigation.navigate(route.name, route.params);
              }}
              onLongPress={() =>
                navigation.emit({ type: "tabLongPress", target: route.key })
              }
              style={({ pressed }) => [
                styles.tab,
                { opacity: pressed ? 0.65 : 1 },
              ]}
            >
              <View
                style={[
                  styles.icon,
                  {
                    backgroundColor: focused ? colors.accentBg : "transparent",
                    borderRadius: radii.md,
                  },
                ]}
              >
                <Ionicons
                  name={icon}
                  size={21}
                  color={focused ? colors.accent : colors.textSubtle}
                />
              </View>
              <Text
                style={[
                  typography.tab,
                  {
                    color: focused ? colors.accent : colors.textMuted,
                    textAlign: "center",
                  },
                ]}
              >
                {label}
              </Text>
              <View
                style={{
                  height: 3,
                  width: 16,
                  borderRadius: 2,
                  backgroundColor: focused ? colors.accent : "transparent",
                }}
              />
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    borderWidth: 1,
    padding: 4,
    width: "100%",
    maxWidth: 680,
    alignSelf: "center",
  },
  tab: {
    flex: 1,
    minWidth: 0,
    minHeight: 68,
    alignItems: "center",
    justifyContent: "center",
    gap: 3,
    paddingVertical: 4,
  },
  icon: {
    width: 42,
    height: 30,
    alignItems: "center",
    justifyContent: "center",
  },
});
