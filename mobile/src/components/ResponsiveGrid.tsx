import React from 'react';
import { View } from 'react-native';

export function ResponsiveGrid({ columns, children }: { columns: number; children: React.ReactNode }) {
  return <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -8, marginVertical: -8 }}>
    {React.Children.toArray(children).map((child, index) => <View key={React.isValidElement(child) && child.key != null ? child.key : index}
      style={{ width: `${100 / columns}%`, padding: 8, minWidth: 0 }}>{child}</View>)}
  </View>;
}
