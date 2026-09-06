import type { Metadata } from "next";
import { Noto_Serif_Georgian, Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

const storyFont = Noto_Serif_Georgian({
  subsets: ["georgian", "latin"],
  weight: ["400", "500", "600"],
  variable: "--font-story",
  display: "swap",
});

const uiFont = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ui",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ილუზიების გარეშე — Stories that reveal the reader",
  description:
    "An interactive literary experience where the story doesn't change. You do.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ka" className={`${storyFont.variable} ${uiFont.variable}`}>
      <body className="font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
