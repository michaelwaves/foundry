import { Head } from 'nextra/components'
import { Footer, Navbar, Layout } from 'nextra-theme-docs'
import { getPageMap } from 'nextra/page-map'
import 'nextra-theme-docs/style.css'

const navbar = <Navbar logo={<span style={{ fontWeight: 700, letterSpacing: '-0.02em' }}>Saffron</span>} />
const footer = <Footer>© {new Date().getFullYear()} RoseTTACommons. MIT License.</Footer>

export default async function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Head />
      <Layout
        navbar={navbar}
        pageMap={await getPageMap()}
        docsRepositoryBase="https://github.com/RoseTTAFold3/foundry"
        footer={footer}
      >
        {children}
      </Layout>
    </>
  )
}
