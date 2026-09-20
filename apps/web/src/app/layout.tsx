import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import { AppStateProvider } from "@/contexts/AppStateProvider";
import { ToastProvider } from "@/components/overlays/Toast";
import "./globals.css";

// ---------------------------------------------------------------------------
// Fonts — loaded via next/font for zero layout shift and self-hosting.
// --font-inter and --font-jetbrains-mono are consumed in globals.css @theme.
// ---------------------------------------------------------------------------

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export const metadata: Metadata = {
  title: {
    default: "OntDekker — Guides & Expeditions",
    template: "%s | OntDekker",
  },
  description:
    "Plan expeditions and connect with verified local guides on OntDekker.",
  keywords: ["slow travel", "expedition", "guides", "adventure"],
  openGraph: {
    siteName: "OntDekker",
    type: "website",
  },
};

// ---------------------------------------------------------------------------
// Root layout
//
// Provider nesting (outer → inner):
//   Providers          — QueryClientProvider + AuthProvider (feature/auth-user)
//     AppStateProvider — Global guide/expedition/user state (develop)
//       ToastProvider  — useToast() for any descendant component (develop)
// ---------------------------------------------------------------------------

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background antialiased">
        <Providers>
          <AppStateProvider>
            <ToastProvider>
              {children}
            </ToastProvider>
          </AppStateProvider>
        </Providers>
      </body>
    </html>
  );
}
