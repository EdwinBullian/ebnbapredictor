import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EB NBA Predictor",
  description: "AI-powered NBA player stat predictions",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-tv-bg text-tv-text antialiased">
        {children}
      </body>
    </html>
  );
}
