import type { Metadata } from "next";
import { Public_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Public Sans over IBM Plex Sans -- it's the U.S. government's own
// accessibility-first typeface (USWDS), built for exactly this brief: an
// official-feeling civic service that has to read easily for everyone, not
// just people with young eyes. IBM Plex Mono stays for numerals -- tabular
// figures matter more than family-matching once times and fares are laid
// out in their own labeled cells rather than inline in prose.
const publicSans = Public_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-numerals",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Saarthi",
  description: "A conversational agent for Indian Railways that watches your journey.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${publicSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-surface text-ink">{children}</body>
    </html>
  );
}
