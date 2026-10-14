import { useWindowDimensions } from 'react-native';

export function useResponsiveLayout() {
  const { width } = useWindowDimensions();
  const isMobile = width < 768;
  const isDesktop = width >= 1024;
  const sidebarWidth = isMobile ? 0 : isDesktop ? 250 : 80;
  const pagePadding = isMobile ? 16 : isDesktop ? 32 : 24;
  const contentWidth = Math.min(1600, width - sidebarWidth - pagePadding * 2);
  const columns = isMobile ? 1 : isDesktop && contentWidth >= 1120 ? 3 : 2;

  return { width, isMobile, isDesktop, sidebarWidth, pagePadding, contentWidth, columns };
}
