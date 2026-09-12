import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import {
  Activity,
  Apple,
  CalendarDays,
  Dumbbell,
  Flag,
  LayoutDashboard,
  LineChart,
  Settings,
  UserRound,
  ClipboardList,
  BookOpen,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

const desktopNav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/today', label: 'Today', icon: CalendarDays },
  { to: '/workouts', label: 'Workouts', icon: Dumbbell },
  { to: '/program', label: 'Program', icon: ClipboardList },
  { to: '/exercises', label: 'Exercises', icon: BookOpen },
  { to: '/body', label: 'Body', icon: UserRound },
  { to: '/nutrition', label: 'Nutrition', icon: Apple },
  { to: '/progress', label: 'Progress', icon: LineChart },
  { to: '/reports', label: 'Reports', icon: Activity },
  { to: '/goals', label: 'Goals', icon: Flag },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const mobileNav = [
  { to: '/today', label: 'Today', icon: CalendarDays },
  { to: '/workouts', label: 'Workout', icon: Dumbbell },
  { to: '/nutrition', label: 'Nutrition', icon: Apple },
  { to: '/progress', label: 'Progress', icon: LineChart },
]

export function AppShell() {
  const { profile, loading } = useAuth()
  const loc = useLocation()

  if (loading) {
    return <div className="grid min-h-svh place-items-center text-muted">Loading…</div>
  }
  if (!profile) {
    return <Navigate to="/login" replace />
  }
  if (!profile.onboarding_completed && loc.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }

  const gym = loc.pathname.startsWith('/gym')

  return (
    <div className="min-h-svh bg-bg text-ink">
      {!gym && (
        <aside className="fixed inset-y-0 left-0 hidden w-56 border-r border-line bg-bg-raised lg:flex lg:flex-col">
          <div className="px-5 py-5 text-lg font-semibold tracking-tight">Fitness</div>
          <nav className="flex-1 space-y-0.5 px-3">
            {desktopNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted hover:bg-bg-overlay hover:text-ink',
                    isActive && 'bg-bg-overlay text-ink',
                  )
                }
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="border-t border-line px-4 py-4 text-sm text-muted">{profile.user.name}</div>
        </aside>
      )}
      <main className={cn(gym ? '' : 'lg:pl-56', gym ? '' : 'pb-20 lg:pb-8')}>
        <Outlet />
      </main>
      {!gym && (
        <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-line bg-bg-raised/95 backdrop-blur lg:hidden">
          {mobileNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn('flex flex-col items-center gap-1 py-2.5 text-[11px] text-muted', isActive && 'text-accent')
              }
            >
              <item.icon size={22} />
              {item.label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}
