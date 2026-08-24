import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// IBM Plex over Inter/JetBrains Mono -- Plex has real engineering
// character (built for a systems company, not a SaaS landing page) and
// the sans/mono pairing shares one designer's hand, so numerals sitting
// next to prose never feel like a bolted-on second typeface.
const plexSans = IBM_Plex_Sans({
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
      className={`${plexSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-surface text-ink">{children}</body>
    </html>
  );
}
