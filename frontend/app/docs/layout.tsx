import { Banner } from 'nextra/components'
import { Footer, Navbar, Layout } from 'nextra-theme-docs'
import { getPageMap } from 'nextra/page-map'
import 'nextra-theme-docs/style.css'

const banner = <Banner storageKey="some-key">Nextra 4.0 is released 🎉</Banner>
const navbar = <Navbar logo={<b>Foundry</b>} />
const footer = <Footer>MIT {new Date().getFullYear()} © Foundry.</Footer>

export default async function DocsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <Layout
      banner={banner}
      navbar={navbar}
      pageMap={await getPageMap('/docs')}
      docsRepositoryBase="https://github.com/michaelwaves/foundry"
      footer={footer}
    >
      {children}
    </Layout>
  )
}
