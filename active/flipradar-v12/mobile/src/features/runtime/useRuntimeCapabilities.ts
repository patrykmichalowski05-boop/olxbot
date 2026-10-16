import { useQuery } from "@tanstack/react-query";
import { getAccount, getPublicConfig } from "@/api/endpoints/portal";
import { useAuth } from "@/features/auth/AuthContext";
import { portalEnabled } from "@/utils/config";
import { readCapabilities } from "./capabilities";

export function useRuntimeCapabilities() {
  const { mode, ready: authReady, signedIn, userId } = useAuth();
  const enabled = mode === "live" && portalEnabled();
  const query = useQuery({
    queryKey: ["portal-public-config"],
    queryFn: getPublicConfig,
    enabled,
    staleTime: 60000,
  });
  const account = useQuery({
    queryKey: ["portal-account", userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled: enabled && authReady && signedIn,
  });
  const declared =
    query.data?.capabilities || account.data?.capabilities
      ? {
          ...query.data?.capabilities,
          ...account.data?.capabilities,
          read_only:
            query.data?.capabilities?.read_only === true ||
            account.data?.capabilities?.read_only === true,
        }
      : undefined;
  const capabilities = readCapabilities(
    declared,
    enabled && process.env.EXPO_PUBLIC_FLIP_BACKEND === "flask-v12",
  );
  const ready =
    !enabled || (query.isSuccess && (!signedIn || account.isSuccess));
  return {
    capabilities,
    ready,
    canWrite: ready && !capabilities.read_only,
    query,
    hasError: query.isError || account.isError,
    retry: () => {
      if (enabled) {
        void query.refetch();
        if (signedIn) void account.refetch();
      }
    },
  };
}
