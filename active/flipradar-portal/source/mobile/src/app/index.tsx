import { Redirect } from 'expo-router';
import { Platform } from 'react-native';
import PortalPage from '@/features/portal/PortalPage';

export default function Index() {
  return Platform.OS === 'web' ? <PortalPage page="landing" /> : <Redirect href="/radar" />;
}
