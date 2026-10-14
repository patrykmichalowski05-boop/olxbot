import { useWindowDimensions } from 'react-native';
import { useSyncExternalStore } from 'react';

const subscribe = () => () => undefined;
const clientSnapshot = () => true;
const serverSnapshot = () => false;

export function useResponsiveLayout() {
  const dimensions = useWindowDimensions();
  // The first web hydration uses the same layout as static rendering.
  // Native renders immediately with its measured dimensions.
  const hydrated = useSyncExternalStore(subscribe, clientSnapshot, serverSnapshot);
  const width = hydrated ? dimensions.width : 0;
  const isMobile = width < 768;
  const isDesktop = width >= 1024;
  const sidebarWidth = isMobile ? 0 : isDesktop ? 250 : 80;
  const pagePadding = isMobile ? 16 : isDesktop ? 32 : 24;
  const contentWidth = Math.min(1600, width - sidebarWidth - pagePadding * 2);
  const columns = isMobile ? 1 : isDesktop && contentWidth >= 1120 ? 3 : 2;

  return { width, isMobile, isDesktop, sidebarWidth, pagePadding, contentWidth, columns };
}
