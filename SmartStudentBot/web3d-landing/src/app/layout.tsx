import type { Metadata } from 'next';
import Script from 'next/script';
import './globals.css';

export const metadata: Metadata = {
  title: 'Smart Perugia | Web3D Assistant',
  description: 'The Integrated Smart Platform for Student Life in Perugia',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
      </head>
      <body className="bg-[#050505] text-white antialiased overflow-x-hidden selection:bg-cyan-500/30">
        {children}
      </body>
    </html>
  );
}
