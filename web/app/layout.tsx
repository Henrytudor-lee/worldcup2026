import type { Metadata } from "next";
import "./globals.css";
import { TabNav } from "./components/TabNav";
import { Header } from "./components/Header";

export const metadata: Metadata = {
  title: "🏆 2026 世界杯预测 · Mavis PDP",
  description: "2026 美加墨世界杯 48 强预测 · 104 场（72 小组 + 32 淘汰）",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <Header />
        <TabNav />
        <main>{children}</main>
      </body>
    </html>
  );
}
