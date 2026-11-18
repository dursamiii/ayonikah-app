import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Ayonikah Planner',
  description: 'A calm space for every wedding detail.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
