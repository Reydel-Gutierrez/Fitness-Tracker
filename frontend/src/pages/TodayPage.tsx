import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Button, Card } from '@/components/ui'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { ExercisePicker } from '@/features/exercises/ExercisePicker'
import { useState } from 'react'

type TodayData = {
  date: string
  is_rest_day: boolean
  planned_workout: { template_id: number; name_override: string | null; template: { name: string; exercises: unknown[]; estimated_duration_minutes: number | null } | null } | null
  existing_sessions: { id: number; name: string; status: string; source: string }[]
  active_session: { id: number } | null
  nutrition: { totals: { calories: number; protein_g: number }; target: { calories: number; protein_g: number } }
  body: { weight: number | null } | null
  goals: { id: number; name: string; current_value: number | null; target_value: number | null; unit: string | null }[]
  is_checkin_day: boolean
  weight_unit: string
}

export function TodayPage() {
  const nav = useNavigate()
  const { profile } = useAuth()
  const { data } = useQuery({ queryKey: ['today'], queryFn: () => api.get<TodayData>('/api/analytics/today') })
  const [quick, setQuick] = useState(false)
  const [quickIds, setQuickIds] = useState<number[]>([])

  if (!data) return <div className="p-6 text-muted">Loading…</div>
  const plannedName = data.planned_workout?.template?.name || data.planned_workout?.name_override
  const inProgress = data.active_session || data.existing_sessions.find((s) => s.status === 'in_progress')

  async function startPlanned() {
    if (!data?.planned_workout) return
    const session = await api.post<{ id: number }>('/api/sessions', {
      template_id: data.planned_workout.template_id,
      source: 'scheduled',
    })
    nav(`/gym/${session.id}`)
  }

  async function startQuick(name: string, ids: number[]) {
    const session = await api.post<{ id: number }>('/api/sessions', { name, source: 'quick', exercise_ids: ids })
    nav(`/gym/${session.id}`)
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 lg:px-8">
      <h1 className="mb-1 text-2xl font-semibold">Today</h1>
      <p className="mb-6 text-sm text-muted">{data.date}</p>
      <Card className="mb-4">
        {inProgress ? (
          <>
            <div className="text-sm text-muted">Workout in progress</div>
            <Button className="mt-3 w-full" size="lg" onClick={() => nav(`/gym/${inProgress.id}`)}>
              Resume workout
            </Button>
          </>
        ) : data.is_rest_day ? (
          <>
            <h2 className="text-xl font-semibold">Rest Day</h2>
            <p className="mt-1 text-sm text-muted">No programmed workout today. Start something extra if you want.</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <Button variant="secondary" onClick={() => void startQuick('Run', [])}>Run</Button>
              <Button variant="secondary" onClick={() => void startQuick('Peloton', [])}>Peloton</Button>
              <Button className="col-span-2" onClick={() => setQuick(true)}>Create Quick Workout</Button>
            </div>
          </>
        ) : (
          <>
            <div className="text-sm text-muted">Today's workout</div>
            <h2 className="text-xl font-semibold">{plannedName}</h2>
            <p className="text-sm text-muted">
              {data.planned_workout?.template?.exercises.length || 0} exercises · {data.planned_workout?.template?.estimated_duration_minutes || '—'} min
            </p>
            <Button className="mt-4 w-full" size="lg" onClick={() => void startPlanned()}>
              Start workout
            </Button>
          </>
        )}
      </Card>
      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <div className="text-xs uppercase text-muted">Calories</div>
          <div className="text-2xl tabular">{formatNumber(data.nutrition.totals.calories, 0)} / {formatNumber(data.nutrition.target.calories, 0)}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-muted">Protein</div>
          <div className="text-2xl tabular">{formatNumber(data.nutrition.totals.protein_g, 0)} / {formatNumber(data.nutrition.target.protein_g, 0)} g</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-muted">Bodyweight</div>
          <div className="text-2xl tabular">{formatNumber(data.body?.weight)} {profile?.weight_unit}</div>
        </Card>
        <Card>
          <div className="text-xs uppercase text-muted">Goals</div>
          {data.goals.length === 0 ? <p className="text-sm text-muted">None yet</p> : data.goals.slice(0, 3).map((g) => (
            <div key={g.id} className="text-sm">{g.name}: {formatNumber(g.current_value)} / {formatNumber(g.target_value)} {g.unit}</div>
          ))}
        </Card>
      </div>
      {data.is_checkin_day && (
        <Button className="mt-4 w-full" variant="secondary" onClick={() => nav('/reports')}>Weekly check-in is due</Button>
      )}
      {quick && (
        <ExercisePicker
          onClose={() => setQuick(false)}
          onSelect={(id) => {
            setQuickIds([...quickIds, id])
            void startQuick('Quick Workout', [...quickIds, id])
            setQuick(false)
          }}
        />
      )}
    </div>
  )
}
