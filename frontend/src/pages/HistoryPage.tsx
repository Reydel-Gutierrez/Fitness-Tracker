import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { formatDuration, formatNumber } from '@/lib/utils'
import type { WorkoutSession } from '@/types'
import { Button } from '@/components/ui'

export function HistoryPage() {
  const { sessionId } = useParams()
  const { data } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.get<WorkoutSession>(`/api/sessions/${sessionId}`),
  })
  if (!data) return <div className="p-6 text-muted">Loading…</div>
  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Link to="/workouts" className="text-sm text-muted">Back</Link>
      <h1 className="mt-2 text-2xl font-semibold">{data.name}</h1>
      <p className="text-sm text-muted">{data.scheduled_date} · {data.status} · {formatDuration(data.duration_seconds)} · volume {formatNumber(data.total_volume)}</p>
      {data.prs?.map((p) => <p key={p} className="text-sm text-accent">{p}</p>)}
      <div className="mt-4 space-y-4">
        {data.exercises.map((ex) => (
          <div key={ex.id} className="rounded-xl border border-line bg-bg-raised p-4">
            <div className="font-medium">{ex.exercise?.name}</div>
            {ex.sets.map((s) => (
              <div key={s.id} className="text-sm tabular text-muted">
                {s.set_number}. {formatNumber(s.weight)} × {s.reps} @ {s.rpe ?? '—'} {s.completed ? '✓' : ''}
              </div>
            ))}
            {ex.cardio && (
              <div className="text-sm text-muted">
                {formatDuration(ex.cardio.duration_seconds)} · {formatNumber(ex.cardio.distance_m)} m · RPE {ex.cardio.rpe ?? '—'}
              </div>
            )}
          </div>
        ))}
      </div>
      {data.status === 'in_progress' && (
        <Button className="mt-4" onClick={() => (window.location.href = `/gym/${data.id}`)}>Resume</Button>
      )}
    </div>
  )
}

export function CalendarPage() {
  const start = new Date()
  start.setDate(1)
  const end = new Date(start.getFullYear(), start.getMonth() + 1, 0)
  const { data = [] } = useQuery({
    queryKey: ['calendar'],
    queryFn: () =>
      api.get<{ date: string; name: string; status: string; session_id: number | null; kind: string }[]>(
        `/api/sessions/calendar?start=${start.toISOString().slice(0, 10)}&end=${end.toISOString().slice(0, 10)}`,
      ),
  })
  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <h1 className="mb-4 text-2xl font-semibold">Calendar</h1>
      <div className="space-y-2">
        {data.map((item, i) => (
          <div key={i} className="flex justify-between rounded-lg border border-line px-3 py-2 text-sm">
            <span>{item.date} · {item.name}</span>
            <span className="text-muted">
              {item.kind}
              {item.session_id && item.status === 'completed' && (
                <Link className="ml-2 text-accent" to={`/history/${item.session_id}`}>Open</Link>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
