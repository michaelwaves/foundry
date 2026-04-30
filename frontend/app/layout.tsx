import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Head } from 'nextra/components'
import { Footer, Navbar, Layout } from 'nextra-theme-docs'
import { getPageMap } from 'nextra/page-map'
import 'nextra-theme-docs/style.css'

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Foundry",
  description: "Foundry documentation",
};

const navbar = <Navbar logo={<span style={{ fontWeight: 700, letterSpacing: '-0.02em' }}>Saffron</span>} />
const footer = <Footer>© {new Date().getFullYear()} RoseTTACommons. MIT License.</Footer>

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      dir="ltr"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <Head />
      <body>
        <Layout
          navbar={navbar}
          pageMap={await getPageMap()}
          docsRepositoryBase="https://github.com/RoseTTAFold3/foundry"
          footer={footer}
        >
          {children}
        </Layout>
      </body>
    </html>
  )
}
