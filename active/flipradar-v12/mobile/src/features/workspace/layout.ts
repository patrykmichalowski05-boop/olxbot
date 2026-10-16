import { createContext, useContext } from "react";
import { useWindowDimensions } from "react-native";
import { layout } from "@/theme/tokens";

export const WorkspaceContext = createContext(false);

export function useWorkspaceLayout() {
  const inside = useContext(WorkspaceContext);
  const { width } = useWindowDimensions();
  const desktop = width >= layout.sidebarBreakpoint;
  const contentWidth = width - (desktop ? layout.sidebarWidth : 0);
  return {
    inside,
    desktop,
    contentWidth,
    narrow: contentWidth < 680,
    pagePadding: desktop ? layout.desktopPadding : layout.mobilePadding,
  };
}
