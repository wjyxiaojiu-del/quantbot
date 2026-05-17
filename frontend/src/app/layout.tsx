import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuantBot - 量化交易平台",
  description: "个人量化交易平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
