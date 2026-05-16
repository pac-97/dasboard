import type { Metadata } from "next";
import { Providers } from "@/providers/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "AWS Security Dashboard",
  description: "Enterprise AWS Security Posture Command Center",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
