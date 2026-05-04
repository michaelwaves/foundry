import type { Metadata } from 'next'
import { Geist_Mono, Kaisei_Tokumin, Nunito } from 'next/font/google'
import './globals.css'

const nunito = Nunito({ variable: '--font-nunito', subsets: ['latin'] })
const kaisei = Kaisei_Tokumin({ variable: '--font-kaisei', subsets: ['latin'], weight: ['400', '700'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Raft Bioworks',
  description: 'Design the Nanoparticle Future',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      dir="ltr"
      suppressHydrationWarning
      className={`${nunito.variable} ${kaisei.variable} ${geistMono.variable}`}
    >
      <body className="font-sans">{children}</body>
    </html>
  )
}
