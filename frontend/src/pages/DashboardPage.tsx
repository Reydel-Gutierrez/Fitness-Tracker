import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar } from 'recharts'
import { Card } from '@/components/ui'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import type { ReactNode } from 'react'
import { useState } from 'react'

const RANGES = ['7d', '30d', '3m', '6m', '1y', 'all']

export function DashboardPage() {
  const [range, setRange] = useState('30d')
  const { data } = useQuery({
    queryKey: ['dashboard', range],
    queryFn: () => api.get<Record<string, unknown>>(`/api/analytics/dashboard?range=${range}`),
  })
  if (!data) return <div className="p-6 text-muted">Loading…</div>
  const cards = data.cards as Record<string, number | string | null>
  const weight = (data.weight_trend as { date: string; weight: number }[]) || []
  const volume = (data.volume_by_week as { week: string; volume: number }[]) || []
  const recent = (data.recent_workouts as { id: number; name: string; date: string; status: string }[]) || []
  const prs = (data.recent_prs as { date: string; exercise: string; value: number; reps: number }[]) || []
  const goals = (data.goals as { id: number; name: string; current_value: number; target_value: number; unit: string }[]) || []

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button key={r} onClick={() => setRange(r)} className={`rounded-full px-3 py-1 text-xs uppercase ${range === r ? 'bg-accent text-bg' : 'text-muted'}`}>
              {r}
            </button>
          ))}
        </div>
      </div>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Body Weight" value={`${formatNumber(cards.body_weight as number)} ${cards.weight_unit || ''}`} />
        <Stat label="Workouts This Week" value={`${cards.workouts_this_week ?? 0}${cards.scheduled_this_week ? ` / ${cards.scheduled_this_week}` : ''}`} />
        <Stat label="Calories Today" value={`${formatNumber(cards.calories_today as number, 0)} / ${formatNumber(cards.calories_target as number, 0)}`} />
        <Stat label="Protein Today" value={`${formatNumber(cards.protein_today as number, 0)} / ${formatNumber(cards.protein_target as number, 0)} g`} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 font-medium">Weight Trend</h2>
          {weight.length ? (
            <ChartLine data={weight} x="date" y="weight" />
          ) : (
            <Empty>Log a bodyweight entry to see this chart.</Empty>
          )}
        </Card>
        <Card>
          <h2 className="mb-3 font-medium">Weekly Training Volume</h2>
          {volume.length ? <ChartBar data={volume} x="week" y="volume" /> : <Empty>Complete a strength workout to see volume.</Empty>}
        </Card>
        <Card>
          <h2 className="mb-3 font-medium">Recent Workouts</h2>
          {recent.length === 0 && <Empty>No sessions yet.</Empty>}
          <ul className="space-y-2 text-sm">
            {recent.map((w) => (
              <li key={w.id}>
                <Link to={`/history/${w.id}`} className="flex justify-between">
                  <span>{w.name}</span>
                  <span className="text-muted">{w.date} · {w.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="mb-3 font-medium">Recent PRs</h2>
          {prs.length === 0 && <Empty>PRs appear after completed sessions.</Empty>}
          <ul className="space-y-2 text-sm">
            {prs.map((p, i) => (
              <li key={i} className="flex justify-between">
                <span>{p.exercise}</span>
                <span className="tabular">{formatNumber(p.value)} × {p.reps}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="mb-3 font-medium">Active Goals</h2>
          {goals.length === 0 && <Empty>Create a goal to track it here.</Empty>}
          {goals.map((g) => (
            <div key={g.id} className="mb-2 text-sm">
              {g.name}: {formatNumber(g.current_value)} / {formatNumber(g.target_value)} {g.unit}
            </div>
          ))}
        </Card>
        <Card>
          <h2 className="mb-3 font-medium">Nutrition Adherence</h2>
          <p className="text-sm text-muted">Calories {formatNumber(cards.calories_today as number, 0)} of {formatNumber(cards.calories_target as number, 0)} today.</p>
        </Card>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular">{value}</div>
    </Card>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted">{children}</p>
}

function ChartLine({ data, x, y }: { data: object[]; x: string; y: string }) {
  return (
    <div className="h-48">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <CartesianGrid stroke="#2a3440" vertical={false} />
          <XAxis dataKey={x} tick={{ fill: '#8b97a4', fontSize: 11 }} />
          <YAxis tick={{ fill: '#8b97a4', fontSize: 11 }} />
          <Tooltip contentStyle={{ background: '#171d24', border: '1px solid #2a3440' }} />
          <Area type="monotone" dataKey={y} stroke="#3d9d8f" fill="#3d9d8f33" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function ChartBar({ data, x, y }: { data: object[]; x: string; y: string }) {
  return (
    <div className="h-48">
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid stroke="#2a3440" vertical={false} />
          <XAxis dataKey={x} tick={{ fill: '#8b97a4', fontSize: 11 }} />
          <YAxis tick={{ fill: '#8b97a4', fontSize: 11 }} />
          <Tooltip contentStyle={{ background: '#171d24', border: '1px solid #2a3440' }} />
          <Bar dataKey={y} fill="#3d9d8f" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
