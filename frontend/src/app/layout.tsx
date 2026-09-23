import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Trading Lab · Prishi", template: "%s · Trading Lab" },
  description: "Private paper-trading research and progress dashboard.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
