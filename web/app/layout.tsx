import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Shell } from "@/components/layout";
import "./globals.css";

export const metadata: Metadata = {
  title: "EvidenceSearch — Scientific literature, intelligently ranked",
  description: "Find and inspect scientific evidence using a rigorously evaluated hybrid retrieval system.",
  icons: { icon: "/favicon.svg" },
};
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body><Shell>{children}</Shell></body></html>;
}
