import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import "./globals.css";
import "./samples.css";

export const metadata: Metadata = {
  title: "TraceLens AI",
  description: "Evidence-grounded incident investigation",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
