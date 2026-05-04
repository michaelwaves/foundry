'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, type ComponentType } from 'react'
import { LogOut, PanelLeftClose, PanelLeftOpen, Sparkles, ListChecks } from 'lucide-react'
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
      data-collapsed={collapsed}
      className={cn(
        'group/sidebar sticky top-0 flex h-dvh shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 ease-out',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <SidebarHeader collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      <nav className="flex flex-1 flex-col gap-1 px-2 py-4">
        {NAV_ITEMS.map((item) => (
          <SidebarLink key={item.href} item={item} active={isActive(pathname, item.href)} collapsed={collapsed} />
        ))}
      </nav>
      <SidebarFooter collapsed={collapsed} />
    </aside>
  )
}

function SidebarHeader({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <div className="flex h-14 items-center gap-2 px-3 border-b border-sidebar-border">
      {!collapsed && (
        <span className="flex-1 text-sm font-semibold tracking-tight truncate">Saffron</span>
      )}
      <button
        type="button"
        onClick={onToggle}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
      >
        {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
      </button>
    </div>
  )
}

function SidebarLink({ item, active, collapsed }: { item: NavItem; active: boolean; collapsed: boolean }) {
  const Icon = item.icon
  return (
    <Link
      href={item.href}
      title={collapsed ? item.label : undefined}
      className={cn(
        'group/link relative flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors',
        active
          ? 'bg-sidebar-primary text-sidebar-primary-foreground'
          : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className={cn('truncate transition-opacity duration-150', collapsed && 'opacity-0 pointer-events-none')}>
        {item.label}
      </span>
    </Link>
  )
}

function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="border-t border-sidebar-border p-2">
      <form action="/auth/logout" method="post">
        <button
          type="submit"
          title={collapsed ? 'Logout' : undefined}
          className="flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-medium text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span className={cn('truncate transition-opacity duration-150', collapsed && 'opacity-0 pointer-events-none')}>
            Logout
          </span>
        </button>
      </form>
    </div>
  )
}

function isActive(pathname: string | null, href: string) {
  if (!pathname) return false
  return pathname === href || pathname.startsWith(`${href}/`)
}
