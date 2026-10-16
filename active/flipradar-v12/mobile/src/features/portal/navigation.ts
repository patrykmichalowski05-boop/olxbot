const destinations = new Set([
  "radar",
  "watched",
  "analyze",
  "flips",
  "settings",
  "offer",
  "purchase",
  "analytics",
  "notifications",
  "searches",
  "account",
  "bot",
  "market",
]);

export function safeReturnPath(
  value: string | null | undefined,
): string | null {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    /[\\\r\n]/.test(value)
  )
    return null;
  const normalized = value.replace(/^\/\(tabs\)\//, "/");
  const section = normalized.slice(1).split(/[/?#]/)[0];
  return destinations.has(section) ? normalized : null;
}

export function isPublicWebRoute(segments: readonly string[]): boolean {
  const first = segments.filter((segment) => !segment.startsWith("("))[0] ?? "";
  return ["", "index", "login", "register", "info"].includes(first);
}
