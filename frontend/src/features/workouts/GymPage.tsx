import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Pause, Play, Plus, SkipForward, Undo2 } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { api } from '@/lib/api'
import { cn, formatDuration, formatNumber, formatPace } from '@/lib/utils'
import type { PerformedExercise, PerformedSet, WorkoutSession } from '@/types'
import { useAuth } from '@/hooks/useAuth'
import { ExercisePicker } from '@/features/exercises/ExercisePicker'
import { ExerciseImage } from '@/features/exercises/ExerciseImage'

function restKey(sessionId: string) {
  return `ft_rest_${sessionId}`
}

export function remainingSeconds(endsAt: number, now: number) {
  return Math.max(0, Math.ceil((endsAt - now) / 1000))
}

export function GymPage() {
  const { sessionId } = useParams()
  const nav = useNavigate()
  const { profile } = useAuth()
  const [session, setSession] = useState<WorkoutSession | null>(null)
  const [error, setError] = useState('')
  const [now, setNow] = useState(Date.now())
  const [endsAt, setEndsAt] = useState<number | null>(() => {
    const raw = sessionId ? localStorage.getItem(restKey(sessionId)) : null
    return raw ? Number(raw) : null
  })
  const [pausedLeft, setPausedLeft] = useState<number | null>(null)
  const [picker, setPicker] = useState<{ mode: 'add' | 'replace'; exerciseId?: number } | null>(null)
  const wu = profile?.weight_unit || 'lb'

  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(t)
  }, [])

  async function reload() {
    if (!sessionId) return
    const data = await api.get<WorkoutSession>(`/api/sessions/${sessionId}`)
    setSession(data)
  }

  useEffect(() => {
    void reload().catch((e) => setError(e.message))
  }, [sessionId])

  function startRest(seconds: number) {
    if (!sessionId || !seconds) return
    const next = Date.now() + seconds * 1000
    setEndsAt(next)
    setPausedLeft(null)
    localStorage.setItem(restKey(sessionId), String(next))
  }

  function clearRest() {
    setEndsAt(null)
    setPausedLeft(null)
    if (sessionId) localStorage.removeItem(restKey(sessionId))
  }

  const left = endsAt ? remainingSeconds(endsAt, now) : pausedLeft ?? 0
  const resting = Boolean(endsAt && left > 0) || pausedLeft !== null

  async function patchSet(setId: number, body: Record<string, unknown>) {
    if (!sessionId) return
    const data = await api.patch<WorkoutSession>(`/api/sessions/${sessionId}/sets/${setId}`, body)
    setSession(data)
  }

  async function completeSet(ex: PerformedExercise, set: PerformedSet) {
    await patchSet(set.id, {
      weight: set.weight,
      reps: set.reps,
      rpe: set.rpe,
      added_weight: set.added_weight,
      assisted_weight: set.assisted_weight,
      completed: true,
    })
    startRest(set.rest_seconds || 90)
  }

  async function finish() {
    if (!sessionId) return
    await api.post(`/api/sessions/${sessionId}/finish`, {})
    if (sessionId) localStorage.removeItem(restKey(sessionId))
    nav(`/history/${sessionId}`)
  }

  if (!session) return <div className="p-6 text-muted">{error || 'Loading workout…'}</div>

  return (
    <div className="mx-auto min-h-svh max-w-lg bg-bg pb-36 sm:pb-28">
      <header
        className="sticky top-0 z-20 flex items-center justify-between border-b border-line bg-bg/95 px-4 pb-3 backdrop-blur"
        style={{
          paddingTop: 'calc(0.75rem + env(safe-area-inset-top, 0px))',
          paddingLeft: 'max(1rem, env(safe-area-inset-left, 0px))',
          paddingRight: 'max(1rem, env(safe-area-inset-right, 0px))',
        }}
      >
        <button
          className="flex min-h-12 min-w-12 items-center justify-start rounded-lg pr-3 text-sm text-muted active:bg-bg-overlay sm:min-h-0 sm:min-w-0 sm:rounded-none sm:pr-0"
          onClick={() => nav('/today')}
        >
          Exit
        </button>
        <div className="min-w-0 px-2 text-center">
          <div className="truncate text-sm font-semibold">{session.name}</div>
          <div className="text-xs text-muted">{session.exercises.length} exercises</div>
        </div>
        <button className="hidden text-sm text-accent sm:inline-flex" onClick={() => void finish()}>
          Finish
        </button>
        <div className="w-12 sm:hidden" aria-hidden="true" />
      </header>

      {resting && (
        <div className="mx-4 mt-3 rounded-xl border border-line bg-bg-raised px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-wide text-muted">Rest</div>
              <div className="text-3xl font-semibold tabular">{formatDuration(left)}</div>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  if (pausedLeft !== null) {
                    startRest(pausedLeft)
                  } else if (endsAt) {
                    setPausedLeft(left)
                    setEndsAt(null)
                    if (sessionId) localStorage.removeItem(restKey(sessionId))
                  }
                }}
              >
                {pausedLeft !== null ? <Play size={16} /> : <Pause size={16} />}
              </Button>
              <Button size="sm" variant="secondary" onClick={() => startRest(left + 30)}>
                +30s
              </Button>
              <Button size="sm" variant="ghost" onClick={clearRest}>
                <SkipForward size={16} /> Skip
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6 px-4 py-4">
        {session.exercises.map((ex) => (
          <ExerciseBlock
            key={ex.id}
            ex={ex}
            unit={wu}
            onChangeSet={(set, patch) => {
              setSession((cur) => {
                if (!cur) return cur
                return {
                  ...cur,
                  exercises: cur.exercises.map((e) =>
                    e.id === ex.id ? { ...e, sets: e.sets.map((s) => (s.id === set.id ? { ...s, ...patch } : s)) } : e,
                  ),
                }
              })
            }}
            onComplete={(set) => void completeSet(ex, set)}
            onUndo={(set) => void patchSet(set.id, { completed: false })}
            onSkipSet={(set) => void patchSet(set.id, { skipped: true })}
            onAddSet={() =>
              void api.post<WorkoutSession>(`/api/sessions/${session.id}/exercises/${ex.id}/sets`).then(setSession)
            }
            onRemoveSet={(set) =>
              void api.del<WorkoutSession>(`/api/sessions/${session.id}/sets/${set.id}`).then(setSession)
            }
            onCardio={(body) =>
              void api.patch<WorkoutSession>(`/api/sessions/${session.id}/exercises/${ex.id}/cardio`, body).then(setSession)
            }
            onSkipEx={() =>
              void api.post<WorkoutSession>(`/api/sessions/${session.id}/exercises/${ex.id}/skip`).then(setSession)
            }
            onReplace={() => setPicker({ mode: 'replace', exerciseId: ex.id })}
            onAcceptSuggestion={() =>
              ex.suggestion && void api.post(`/api/sessions/recommendations/${ex.suggestion.id}`, { status: 'accepted' }).then(reload)
            }
            onIgnoreSuggestion={() =>
              ex.suggestion && void api.post(`/api/sessions/recommendations/${ex.suggestion.id}`, { status: 'ignored' }).then(reload)
            }
          />
        ))}
        <Button variant="secondary" className="w-full" onClick={() => setPicker({ mode: 'add' })}>
          <Plus size={16} /> Add exercise
        </Button>
      </div>

      <div
        className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-bg/95 px-4 pt-3 backdrop-blur sm:hidden"
        style={{
          paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom, 0px))',
          paddingLeft: 'max(1rem, env(safe-area-inset-left, 0px))',
          paddingRight: 'max(1rem, env(safe-area-inset-right, 0px))',
        }}
      >
        <div className="mx-auto max-w-lg">
          <Button className="h-14 w-full text-base font-semibold" onClick={() => void finish()}>
            Finish Workout
          </Button>
        </div>
      </div>

      {picker && sessionId && (
        <ExercisePicker
          onClose={() => setPicker(null)}
          onSelect={async (id) => {
            if (picker.mode === 'add') await api.post(`/api/sessions/${sessionId}/exercises`, { exercise_id: id })
            else if (picker.exerciseId) await api.post(`/api/sessions/${sessionId}/exercises/${picker.exerciseId}/replace`, { exercise_id: id })
            setPicker(null)
            await reload()
          }}
        />
      )}
    </div>
  )
}

function ExerciseBlock({
  ex,
  unit,
  onChangeSet,
  onComplete,
  onUndo,
  onSkipSet,
  onAddSet,
  onRemoveSet,
  onCardio,
  onSkipEx,
  onReplace,
  onAcceptSuggestion,
  onIgnoreSuggestion,
}: {
  ex: PerformedExercise
  unit: string
  onChangeSet: (set: PerformedSet, patch: Partial<PerformedSet>) => void
  onComplete: (set: PerformedSet) => void
  onUndo: (set: PerformedSet) => void
  onSkipSet: (set: PerformedSet) => void
  onAddSet: () => void
  onRemoveSet: (set: PerformedSet) => void
  onCardio: (body: Record<string, unknown>) => void
  onSkipEx: () => void
  onReplace: () => void
  onAcceptSuggestion: () => void
  onIgnoreSuggestion: () => void
}) {
  const type = ex.exercise?.exercise_type || 'strength'
  const isCardio = type === 'cardio' || type === 'timed' || type === 'distance'
  const current = ex.sets.find((s) => !s.completed && !s.skipped)
  const done = ex.sets.filter((s) => s.completed).length

  return (
    <section className={cn('rounded-2xl border border-line bg-bg-raised p-4', ex.skipped && 'opacity-50')}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <ExerciseImage
            src={ex.exercise?.thumbnail || ex.exercise?.images?.[0]}
            alt={ex.exercise?.name || ''}
            size={64}
            className="h-16 w-16 shrink-0 rounded-lg"
          />
          <div className="min-w-0">
            <h2 className="text-lg font-semibold leading-tight">{ex.exercise?.name}</h2>
            <p className="text-xs text-muted">
              {isCardio ? type : `Set ${current ? current.set_number : done} / ${ex.sets.length}`}
            </p>
          </div>
        </div>
        <div className="flex gap-2 text-xs">
          <button className="text-muted" onClick={onReplace}>
            Replace
          </button>
          <button className="text-muted" onClick={onSkipEx}>
            {ex.skipped ? 'Unskip' : 'Skip'}
          </button>
        </div>
      </div>

      {ex.suggestion && ex.suggestion.status === 'pending' && (
        <div className="mb-3 rounded-lg border border-line bg-bg-overlay p-3 text-sm">
          <div className="font-medium">Suggested next time: {formatNumber(ex.suggestion.suggested_weight)} {unit}</div>
          <p className="mt-1 text-muted">{ex.suggestion.reason}</p>
          <div className="mt-2 flex gap-2">
            <Button size="sm" onClick={onAcceptSuggestion}>Accept</Button>
            <Button size="sm" variant="ghost" onClick={onIgnoreSuggestion}>Ignore</Button>
          </div>
        </div>
      )}

      {isCardio ? (
        <CardioBlock ex={ex} onCardio={onCardio} />
      ) : (
        <div className="space-y-2">
          <div className="grid grid-cols-[2rem_1fr_1fr_1fr] gap-2 text-[11px] uppercase tracking-wide text-muted">
            <span>#</span>
            <span>Target / last</span>
            <span>Today</span>
            <span></span>
          </div>
          {ex.sets.map((set) => {
            const prev = ex.previous_sets.find((p) => p.set_number === set.set_number)
            return (
              <div key={set.id} className={cn('grid grid-cols-[2rem_1fr_1fr_auto] items-center gap-2 rounded-lg p-1', set.completed && 'opacity-70')}>
                <div className={cn('text-sm tabular', set.completed && 'text-accent')}>{set.completed ? '✓' : set.set_number}</div>
                <div className={cn('text-xs text-muted', set.completed && 'line-through')}>
                  <div>
                    {set.target_reps ?? '—'} {set.target_effort || ''} {set.target_rpe ? `RPE ${set.target_rpe}` : ''}
                  </div>
                  <div>
                    Last:{' '}
                    {prev
                      ? `${formatNumber(prev.weight)} × ${prev.reps ?? '—'}`
                      : '—'}
                  </div>
                </div>
                <div className="flex gap-1">
                  {type !== 'bodyweight' && (
                    <Input
                      className="h-12 w-16 px-1 text-center text-base"
                      inputMode="decimal"
                      value={set.weight ?? ''}
                      onChange={(e) => onChangeSet(set, { weight: e.target.value === '' ? null : Number(e.target.value) })}
                      aria-label="Weight"
                    />
                  )}
                  {type === 'bodyweight' && (
                    <Input
                      className="h-12 w-16 px-1 text-center text-base"
                      inputMode="decimal"
                      placeholder="+w"
                      value={set.added_weight ?? ''}
                      onChange={(e) => onChangeSet(set, { added_weight: e.target.value === '' ? null : Number(e.target.value) })}
                    />
                  )}
                  <Input
                    className="h-12 w-14 px-1 text-center text-base"
                    inputMode="numeric"
                    value={set.reps ?? ''}
                    onChange={(e) => onChangeSet(set, { reps: e.target.value === '' ? null : Number(e.target.value) })}
                    aria-label="Reps"
                  />
                  <Input
                    className="h-12 w-12 px-1 text-center text-base"
                    inputMode="decimal"
                    placeholder="RPE"
                    value={set.rpe ?? ''}
                    onChange={(e) => onChangeSet(set, { rpe: e.target.value === '' ? null : Number(e.target.value) })}
                    aria-label="RPE"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  {set.completed ? (
                    <Button size="sm" variant="ghost" onClick={() => onUndo(set)} aria-label="Undo">
                      <Undo2 size={16} />
                    </Button>
                  ) : (
                    <Button size="sm" className="h-12 w-12" onClick={() => onComplete(set)} aria-label="Complete set">
                      ✓
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
          <div className="flex gap-2 pt-1">
            <Button size="sm" variant="secondary" onClick={onAddSet}>Add set</Button>
            {current && (
              <Button size="sm" variant="ghost" onClick={() => onSkipSet(current)}>
                Skip set
              </Button>
            )}
            {ex.sets.length > 1 && (
              <Button size="sm" variant="ghost" onClick={() => onRemoveSet(ex.sets[ex.sets.length - 1])}>
                Remove set
              </Button>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

function CardioBlock({ ex, onCardio }: { ex: PerformedExercise; onCardio: (body: Record<string, unknown>) => void }) {
  const cardio = ex.cardio
  const [duration, setDuration] = useState(String(cardio?.duration_seconds ? Math.round((cardio.duration_seconds || 0) / 60) : cardio?.target_duration_seconds ? Math.round((cardio.target_duration_seconds || 0) / 60) : ''))
  const [distance, setDistance] = useState(String(cardio?.distance_m ? (cardio.distance_m || 0) / 1000 : ''))
  const [calories, setCalories] = useState(String(cardio?.calories ?? ''))
  const [hr, setHr] = useState(String(cardio?.avg_hr ?? ''))
  const [resistance, setResistance] = useState(cardio?.resistance ?? '')
  const [rpe, setRpe] = useState(String(cardio?.rpe ?? ''))
  const type = ex.exercise?.exercise_type

  return (
    <div className="space-y-3">
      <div className="text-sm text-muted">
        Target: {cardio?.target_duration_seconds ? formatDuration(cardio.target_duration_seconds) : '—'} {cardio?.target_effort || ''}
        {ex.previous_cardio?.duration_seconds ? ` · Last ${formatDuration(ex.previous_cardio.duration_seconds)}` : ''}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-muted">
          Duration (min)
          <Input value={duration} inputMode="decimal" onChange={(e) => setDuration(e.target.value)} className="mt-1 h-12" />
        </label>
        {(type === 'distance' || type === 'cardio') && (
          <label className="text-xs text-muted">
            Distance (km)
            <Input value={distance} inputMode="decimal" onChange={(e) => setDistance(e.target.value)} className="mt-1 h-12" />
          </label>
        )}
        <label className="text-xs text-muted">
          Calories
          <Input value={calories} inputMode="decimal" onChange={(e) => setCalories(e.target.value)} className="mt-1 h-12" />
        </label>
        <label className="text-xs text-muted">
          Avg HR
          <Input value={hr} inputMode="numeric" onChange={(e) => setHr(e.target.value)} className="mt-1 h-12" />
        </label>
        <label className="text-xs text-muted">
          Resistance
          <Input value={resistance} onChange={(e) => setResistance(e.target.value)} className="mt-1 h-12" />
        </label>
        <label className="text-xs text-muted">
          RPE
          <Input value={rpe} inputMode="decimal" onChange={(e) => setRpe(e.target.value)} className="mt-1 h-12" />
        </label>
      </div>
      {distance && duration && (
        <p className="text-sm text-muted">
          Pace {formatPace((Number(duration) * 60) / Math.max(Number(distance), 0.001))}
        </p>
      )}
      <Button
        className="h-14 w-full"
        onClick={() =>
          onCardio({
            duration_seconds: duration ? Math.round(Number(duration) * 60) : null,
            distance_m: distance ? Number(distance) * 1000 : null,
            calories: calories ? Number(calories) : null,
            avg_hr: hr ? Number(hr) : null,
            resistance: resistance || null,
            rpe: rpe ? Number(rpe) : null,
            completed: true,
          })
        }
      >
        {cardio?.completed ? 'Update cardio' : 'Complete cardio'}
      </Button>
    </div>
  )
}
