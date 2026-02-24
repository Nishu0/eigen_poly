import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Eigen Poly",
  description: "Verifiable intent engines for prediction market agents"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
