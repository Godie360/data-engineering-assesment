import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sele the Analyst — Selcom Data Intelligence",
  description: "Ask Sele anything about Selcom mobile money transaction data. Powered by Text-to-SQL and GPT-4o-mini.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased">{children}</body>
    </html>
  );
}
