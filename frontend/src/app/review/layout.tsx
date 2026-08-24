import type { ReactNode } from 'react';
import { Inter, Space_Grotesk } from 'next/font/google';

// Light theme uses Inter throughout; dark theme uses Space Grotesk for headings.
const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '600', '700', '800'],
  variable: '--font-review-inter',
  display: 'swap',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['500', '700'],
  variable: '--font-review-heading',
  display: 'swap',
});

export default function ReviewLayout({ children }: { children: ReactNode }) {
  return <div className={`${inter.variable} ${spaceGrotesk.variable}`}>{children}</div>;
}
