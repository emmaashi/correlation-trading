import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Correlation Trading",
  description:
    "Lagged correlations and statistical trading signals between stock pairs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark !scroll-smooth">
      <body className="min-h-screen bg-black text-neutral-50 antialiased">
        {children}
      </body>
    </html>
  );
}
