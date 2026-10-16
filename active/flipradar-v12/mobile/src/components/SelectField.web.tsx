import React, { useId, useState } from "react";
import { useTheme } from "@/theme/ThemeProvider";

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
  const id = useId();
  const [focused, setFocused] = useState(false);
  const { colors, radii } = useTheme();
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minWidth: 0,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <label
        htmlFor={id}
        style={{
          fontSize: 12,
          lineHeight: "16px",
          fontWeight: 600,
          color: colors.textMuted,
        }}
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.currentTarget.value as T)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          minHeight: 44,
          width: "100%",
          minWidth: 0,
          border: `1px solid ${focused ? colors.focus : colors.border}`,
          borderRadius: radii.md,
          background: colors.surface,
          color: colors.text,
          font: "inherit",
          fontSize: 14,
          padding: "0 12px",
          cursor: "pointer",
          boxSizing: "border-box",
          outlineColor: colors.focus,
          outlineOffset: 2,
        }}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
