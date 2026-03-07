import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "BRP Cyber Objective Gate",
  description: "Enterprise orchestration readiness dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="grid-noise">
        <nav className="mx-auto flex w-full max-w-7xl items-center gap-3 px-4 py-3 text-xs sm:px-6 lg:px-8">
          <Link href="/" className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 hover:border-slate-500">
            Dashboard
          </Link>
          <Link
            href="/configuration"
            className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 hover:border-slate-500"
          >
            Configuration
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
