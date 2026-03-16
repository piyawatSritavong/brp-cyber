import type { Metadata } from "next";
import { AppChrome } from "@/components/AppChrome";
import "./globals.css";

export const metadata: Metadata = {
  title: "BRP Cyber Objective Gate",
  description: "Enterprise orchestration readiness dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light">
      <body>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
