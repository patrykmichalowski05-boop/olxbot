import React from 'react';
import { AppScreen } from '@/components/AppScreen';
import { Header } from '@/components/Header';
import { DemoBanner } from '@/components/DemoBanner';

export default function DashboardScreen() {
  return <AppScreen scroll><Header title="Dashboard" subtitle="Przegląd okazji i Twoich flipów" /><DemoBanner /></AppScreen>;
}
