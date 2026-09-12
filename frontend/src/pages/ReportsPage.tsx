import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Card, Field, Input, Textarea } from '@/components/ui'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

type Report = {
  week_start: string
  week_end: string
  sentences: string[]
  body: Record<string, number | string | null>
  training: Record<string, number | null>
  strength: { name: string; e1rm: number; e1rm_prev: number | null }[]
  prs: string[]
  cardio: Record<string, number>
  nutrition: Record<string, number | null>
  goals: { name: string; current_value: number; target_value: number; unit: string }[]
}

export function ReportsPage() {
  const { profile } = useAuth()
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['report'], queryFn: () => api.get<Report>('/api/reports/weekly') })
  const [form, setForm] = useState<Record<string, string>>({})

  async function checkin() {
    await api.post('/api/checkins', {
      weight: form.weight ? Number(form.weight) : null,
      body_fat_pct: form.body_fat_pct ? Number(form.body_fat_pct) : null,
      waist: form.waist ? Number(form.waist) : null,
      chest: form.chest ? Number(form.chest) : null,
      neck: form.neck ? Number(form.neck) : null,
      left_arm: form.left_arm ? Number(form.left_arm) : null,
      right_arm: form.right_arm ? Number(form.right_arm) : null,
      hips: form.hips ? Number(form.hips) : null,
      left_thigh: form.left_thigh ? Number(form.left_thigh) : null,
      right_thigh: form.right_thigh ? Number(form.right_thigh) : null,
      left_calf: form.left_calf ? Number(form.left_calf) : null,
      right_calf: form.right_calf ? Number(form.right_calf) : null,
      energy: form.energy ? Number(form.energy) : null,
      sleep_quality: form.sleep_quality ? Number(form.sleep_quality) : null,
      stress: form.stress ? Number(form.stress) : null,
      training_satisfaction: form.training_satisfaction ? Number(form.training_satisfaction) : null,
      notes: form.notes || null,
    })
    void qc.invalidateQueries({ queryKey: ['report'] })
    void qc.invalidateQueries({ queryKey: ['body'] })
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      <h1 className="mb-2 text-2xl font-semibold">Reports</h1>
      <p className="mb-6 text-sm text-muted">Weekly check-in defaults to Friday. Change the day in Settings.</p>
      <Card className="mb-6">
        <h2 className="mb-3 font-medium">Weekly check-in</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {['weight', 'body_fat_pct', 'waist', 'chest', 'neck', 'left_arm', 'right_arm', 'hips', 'left_thigh', 'right_thigh', 'left_calf', 'right_calf'].map((k) => (
            <Field key={k} label={k.replaceAll('_', ' ')}>
              <Input inputMode="decimal" value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            </Field>
          ))}
          {['energy', 'sleep_quality', 'stress', 'training_satisfaction'].map((k) => (
            <Field key={k} label={`${k.replaceAll('_', ' ')} (1-5)`}>
              <Input type="number" min={1} max={5} value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            </Field>
          ))}
          <div className="sm:col-span-2"><Field label="Notes"><Textarea value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field></div>
        </div>
        <Button className="mt-4" onClick={() => void checkin()}>Save check-in</Button>
      </Card>
      {data && (
        <Card>
          <h2 className="mb-1 font-medium">Week of {data.week_start}</h2>
          <ul className="mb-4 list-disc space-y-1 pl-5 text-sm">
            {data.sentences.map((s) => <li key={s}>{s}</li>)}
          </ul>
          <div className="grid gap-3 sm:grid-cols-2 text-sm">
            <div>
              <h3 className="font-medium">Body</h3>
              <p>Weight {formatNumber(data.body.weight as number)} {profile?.weight_unit} (Δ {formatNumber(data.body.weight_change as number)})</p>
              <p>7-day avg {data.body.avg_7d != null ? formatNumber(data.body.avg_7d as number) : 'Not enough data yet to calculate this trend.'}</p>
              <p>Waist Δ {formatNumber(data.body.waist_change as number)}</p>
            </div>
            <div>
              <h3 className="font-medium">Training</h3>
              <p>{data.training.completed} / {data.training.scheduled} workouts</p>
              <p>Volume {formatNumber(data.training.volume as number)} (Δ {formatNumber(data.training.volume_change_pct as number)}%)</p>
              <p>Sets {data.training.sets} · avg RPE {formatNumber(data.training.avg_rpe as number)}</p>
            </div>
            <div>
              <h3 className="font-medium">Cardio</h3>
              <p>{data.cardio.sessions} sessions · {data.cardio.duration_seconds}s · {formatNumber(data.cardio.distance_m)} m</p>
            </div>
            <div>
              <h3 className="font-medium">Nutrition</h3>
              <p>Avg cal {formatNumber(data.nutrition.avg_calories as number, 0)}</p>
              <p>Avg protein {formatNumber(data.nutrition.avg_protein as number, 0)}</p>
              <p>Protein target {data.nutrition.days_protein_target}/{data.nutrition.days_logged} days</p>
            </div>
          </div>
          {data.prs?.length > 0 && (
            <div className="mt-4 text-sm">
              <h3 className="font-medium">Strength</h3>
              {data.prs.map((p) => <p key={p}>{p}</p>)}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
