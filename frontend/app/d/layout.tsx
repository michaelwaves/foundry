import { DashboardSidebar } from '@/components/dashboard-sidebar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      <DashboardSidebar />
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  )
}
