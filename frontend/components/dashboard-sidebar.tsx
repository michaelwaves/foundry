'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, type ComponentType } from 'react'
import { LogOut, PanelLeftClose, PanelLeftOpen, Sparkles, ListChecks } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type NavItem = { href: string; label: string; icon: ComponentType<{ className?: string }> }

const NAV_ITEMS: NavItem[] = [
  { href: '/d/generate', label: 'Generate', icon: Sparkles },
  { href: '/d/jobs', label: 'Jobs', icon: ListChecks },
]

export function DashboardSidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        'sticky top-0 flex h-dvh shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border',
        'transition-[width] duration-300 ease-out',
        collapsed ? 'w-[72px]' : 'w-64',
      )}
    >
      <div className={cn('flex h-16 items-center border-b border-sidebar-border', collapsed ? 'justify-center' : 'justify-between px-4')}>
        {collapsed ? (
          <Image src="/logo.svg" alt="Raft Bioworks" width={30} height={28} priority />
        ) : (
          <Link href="/d/generate" className="flex items-center gap-2 select-none">
            <Image src="/logo.svg" alt="Raft Bioworks" width={30} height={28} priority />
            <span className="font-heading text-xl text-brand-orange tracking-tight">Raft Bioworks</span>
          </Link>
        )}
        {!collapsed && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setCollapsed((v) => !v)}
            aria-label="Collapse sidebar"
            className="text-sidebar-foreground/60 hover:text-brand-orange"
          >
            <PanelLeftClose />
          </Button>
        )}
      </div>
      {collapsed && (
        <div className="flex justify-center px-2 pt-2">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setCollapsed(false)}
            aria-label="Expand sidebar"
            className="text-sidebar-foreground/60 hover:text-brand-orange"
          >
            <PanelLeftOpen />
          </Button>
        </div>
      )}

      <nav className="flex flex-1 flex-col gap-1 p-3">
        {NAV_ITEMS.map((item) => (
          <SidebarLink key={item.href} item={item} active={isActive(pathname, item.href)} collapsed={collapsed} />
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <form action="/auth/logout" method="post">
          <Button
            type="submit"
            variant="ghost"
            size="lg"
            title={collapsed ? 'Logout' : undefined}
            className={cn(
              'w-full text-sidebar-foreground/70 hover:bg-brand-orange/10 hover:text-brand-orange',
              collapsed ? 'justify-center px-0' : 'justify-start',
            )}
          >
            <LogOut />
            {!collapsed && <span>Logout</span>}
          </Button>
        </form>
      </div>
    </aside>
  )
}

function SidebarLink({ item, active, collapsed }: { item: NavItem; active: boolean; collapsed: boolean }) {
  const Icon = item.icon
  return (
    <Link
      href={item.href}
      title={collapsed ? item.label : undefined}
      className={cn(
        'flex h-10 items-center rounded-lg text-sm font-medium transition-colors',
        collapsed ? 'justify-center' : 'gap-3 px-3',
        active
          ? 'bg-brand-orange text-white shadow-sm shadow-brand-orange/30'
          : 'text-sidebar-foreground/75 hover:bg-brand-orange/10 hover:text-brand-orange',
      )}
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  )
}

function isActive(pathname: string | null, href: string) {
  if (!pathname) return false
  return pathname === href || pathname.startsWith(`${href}/`)
}
