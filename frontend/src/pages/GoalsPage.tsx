import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Card, Field, Input } from '@/components/ui'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'

type Goal = {
  id: number
  type: string
  name: string
  start_value: number | null
  current_value: number | null
  target_value: number | null
  unit: string | null
  status: string
  progress_pct: number | null
}

const types = ['weight', 'body_measurement', 'workout_frequency', 'strength', 'cardio', 'nutrition', 'custom']

export function GoalsPage() {
  const qc = useQueryClient()
  const { data = [] } = useQuery({ queryKey: ['goals'], queryFn: () => api.get<Goal[]>('/api/goals') })
  const [form, setForm] = useState({ type: 'weight', name: '', start_value: '', target_value: '', unit: 'lb' })

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 lg:px-8">
      <h1 className="mb-4 text-2xl font-semibold">Goals</h1>
      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <Field label="Type">
          <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            {types.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Bench press 225 lb" /></Field>
        <Field label="Start"><Input value={form.start_value} onChange={(e) => setForm({ ...form, start_value: e.target.value })} /></Field>
        <Field label="Target"><Input value={form.target_value} onChange={(e) => setForm({ ...form, target_value: e.target.value })} /></Field>
        <Field label="Unit"><Input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} /></Field>
      </div>
      <Button onClick={() => void api.post('/api/goals', {
        type: form.type, name: form.name, start_value: Number(form.start_value) || null, current_value: Number(form.start_value) || null, target_value: Number(form.target_value) || null, unit: form.unit,
      }).then(() => qc.invalidateQueries({ queryKey: ['goals'] }))}>Add goal</Button>
      <div className="mt-6 space-y-3">
        {data.map((g) => (
          <Card key={g.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{g.name}</div>
                <div className="text-sm text-muted">{formatNumber(g.current_value)} / {formatNumber(g.target_value)} {g.unit}</div>
              </div>
              <button className="text-xs text-danger" onClick={() => void api.del(`/api/goals/${g.id}`).then(() => qc.invalidateQueries({ queryKey: ['goals'] }))}>Delete</button>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-bg-overlay">
              <div className="h-full bg-accent" style={{ width: `${Math.min(100, g.progress_pct || 0)}%` }} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
