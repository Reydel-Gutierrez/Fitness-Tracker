import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Button, Card, Field, Input, Textarea } from '@/components/ui'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

const fields = [
  ['weight', 'Weight'],
  ['body_fat_pct', 'Body fat %'],
  ['waist', 'Waist'],
  ['chest', 'Chest'],
  ['neck', 'Neck'],
  ['left_arm', 'Left arm'],
  ['right_arm', 'Right arm'],
  ['hips', 'Hips'],
  ['left_thigh', 'Left thigh'],
  ['right_thigh', 'Right thigh'],
  ['left_calf', 'Left calf'],
  ['right_calf', 'Right calf'],
] as const

export function BodyPage() {
  const { profile } = useAuth()
  const qc = useQueryClient()
  const { data: list = [] } = useQuery({ queryKey: ['body'], queryFn: () => api.get<Record<string, unknown>[]>('/api/body') })
  const { data: stats } = useQuery({ queryKey: ['body-stats'], queryFn: () => api.get<{ avg_7d: number | null; trend_30d: number | null; series: { date: string; weight: number }[] }>('/api/body/stats') })
  const [form, setForm] = useState<Record<string, string>>({})

  async function save() {
    const payload: Record<string, number | string | null> = {}
    for (const [k] of fields) {
      payload[k] = form[k] ? Number(form[k]) : null
    }
    payload.notes = form.notes || null
    await api.post('/api/body', payload)
    setForm({})
    void qc.invalidateQueries({ queryKey: ['body'] })
    void qc.invalidateQueries({ queryKey: ['body-stats'] })
  }

  const latest = list[0] as Record<string, number | null> | undefined

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      <h1 className="mb-4 text-2xl font-semibold">Body</h1>
      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Card><div className="text-xs text-muted">Current</div><div className="text-2xl tabular">{formatNumber(latest?.weight)} {profile?.weight_unit}</div></Card>
        <Card><div className="text-xs text-muted">7-day average</div><div className="text-2xl tabular">{stats?.avg_7d != null ? formatNumber(stats.avg_7d) : 'Not enough data yet'}</div></Card>
        <Card><div className="text-xs text-muted">30-day trend</div><div className="text-2xl tabular">{stats?.trend_30d != null ? formatNumber(stats.trend_30d) : 'Not enough data yet'}</div></Card>
      </div>
      <Card className="mb-6">
        {stats?.series?.length ? (
          <div className="h-48">
            <ResponsiveContainer>
              <AreaChart data={stats.series}>
                <CartesianGrid stroke="#2a3440" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: '#8b97a4', fontSize: 11 }} />
                <YAxis tick={{ fill: '#8b97a4', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#171d24', border: '1px solid #2a3440' }} />
                <Area type="monotone" dataKey="weight" stroke="#3d9d8f" fill="#3d9d8f33" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : <p className="text-sm text-muted">No weight history yet.</p>}
      </Card>
      <h2 className="mb-3 font-medium">New entry</h2>
      <p className="mb-3 text-xs text-muted">Weight in {profile?.weight_unit}, lengths in {profile?.length_unit}. Previous records are never overwritten.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {fields.map(([k, label]) => (
          <Field key={k} label={label}>
            <Input inputMode="decimal" value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
          </Field>
        ))}
        <div className="sm:col-span-2">
          <Field label="Notes"><Textarea value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
        </div>
      </div>
      <Button className="mt-4" onClick={() => void save()}>Save measurement</Button>
      <h2 className="mb-3 mt-8 font-medium">History</h2>
      <div className="space-y-2">
        {list.map((row) => (
          <div key={String(row.id)} className="rounded-lg border border-line bg-bg-raised px-4 py-3 text-sm">
            <div className="flex justify-between">
              <span>{String(row.measured_on)}</span>
              <span className="tabular">{formatNumber(row.weight as number)} {profile?.weight_unit}</span>
            </div>
            {row.change ? (
              <div className="text-xs text-muted">
                Δ weight {formatNumber((row.change as Record<string, number>).weight)} · from start {formatNumber((row.change_from_start as Record<string, number> | undefined)?.weight)}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}
