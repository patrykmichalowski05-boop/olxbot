import React from "react";
import { Linking, Platform, View } from "react-native";
import { useRouter } from "expo-router";
import { AppScreen } from "@/components/AppScreen";
import { Header } from "@/components/Header";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PrimaryButton } from "@/components/PrimaryButton";
import type { IconName } from "@/components/IconButton";
import { apiBaseUrl } from "@/utils/config";
import type { BackendCapabilities } from "./capabilities";
import { useRuntimeCapabilities } from "./useRuntimeCapabilities";

export function RuntimeFeature({
  feature,
  title,
  description,
  icon,
  children,
}: {
  feature: keyof Pick<
    BackendCapabilities,
    "watchlist" | "manual_analysis" | "deals" | "deals_read"
  >;
  title: string;
  description: string;
  icon: IconName;
  children: React.ReactNode;
}) {
  const runtime = useRuntimeCapabilities();
  const router = useRouter();
  if (runtime.ready && runtime.capabilities[feature]) return <>{children}</>;
  return (
    <AppScreen scroll>
      <Header title={title} />
      <View style={{ gap: 16 }}>
        {!runtime.ready && !runtime.hasError ? (
          <LoadingSkeleton rows={2} />
        ) : runtime.hasError ? (
          <ErrorState
            message="Nie udało się sprawdzić dostępnych narzędzi. Spróbuj ponownie."
            onRetry={runtime.retry}
          />
        ) : (
          <>
            <EmptyState
              title={title}
              icon={icon}
              description={description}
              actionLabel="Przejdź do radaru"
              onAction={() => router.push("/radar")}
            />
            <PrimaryButton
              label="Otwórz centrum narzędzi"
              variant="secondary"
              icon="open-outline"
              onPress={() => {
                if (Platform.OS === "web")
                  globalThis.location.assign("/centrum?tab=dashboard");
                else
                  void Linking.openURL(
                    `${apiBaseUrl()}/centrum?tab=dashboard`,
                  ).catch(() => undefined);
              }}
            />
          </>
        )}
      </View>
    </AppScreen>
  );
}
