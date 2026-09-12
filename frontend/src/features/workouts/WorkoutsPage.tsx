import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Button, Field, Input, Select, Textarea } from '@/components/ui'
import { api } from '@/lib/api'
import { WEEKDAYS_FULL } from '@/lib/utils'
import type { PrescribedSet, TemplateExercise, WorkoutTemplate, Exercise } from '@/types'
import { ExercisePicker } from '@/features/exercises/ExercisePicker'

export function WorkoutsPage() {
  const { data = [] } = useQuery({
    queryKey: ['workouts'],
    queryFn: () => api.get<WorkoutTemplate[]>('/api/workouts'),
  })
  const { data: activeProgram } = useQuery({
    queryKey: ['program-active'],
    queryFn: () => api.get<{ id: number; name: string; notes: string | null; is_active: boolean; workouts: unknown[] } | null>('/api/programs/active'),
  })
  const qc = useQueryClient()
  const nav = useNavigate()
  const [assignId, setAssignId] = useState<number | null>(null)
  const [assignDay, setAssignDay] = useState(0)
  const [assigning, setAssigning] = useState(false)

  async function addToProgram() {
    if (!activeProgram || assignId == null) return
    setAssigning(true)
    try {
      const program = await api.get<{
        id: number
        name: string
        notes: string | null
        is_active: boolean
        workouts: { template_id: number; weekday: number }[]
      }>(`/api/programs/${activeProgram.id}`)
      await api.put(`/api/programs/${program.id}`, {
        name: program.name,
        notes: program.notes,
        is_active: program.is_active,
        workouts: [
          ...program.workouts.map((w, i) => ({
            template_id: w.template_id,
            weekday: w.weekday,
            position: i,
            name_override: null,
          })),
          { template_id: assignId, weekday: assignDay, position: program.workouts.length, name_override: null },
        ],
      })
      void qc.invalidateQueries({ queryKey: ['programs'] })
      void qc.invalidateQueries({ queryKey: ['program-active'] })
      void qc.invalidateQueries({ queryKey: ['today'] })
      setAssignId(null)
    } finally {
      setAssigning(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Workouts</h1>
        <Link to="/workouts/calendar" className="text-sm text-muted">Calendar</Link>
        <Button onClick={() => nav('/workouts/new')}>New workout</Button>
      </div>
      <div className="space-y-2">
        {data.map((w) => (
          <div key={w.id} className="rounded-xl border border-line bg-bg-raised px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <Link to={`/workouts/${w.id}`} className="font-medium">
                {w.name}
                <div className="text-xs text-muted">
                  {w.exercises.length} exercises · {w.estimated_duration_minutes || '—'} min
                </div>
              </Link>
              <div className="flex shrink-0 flex-wrap justify-end gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    api.post<{ id: number }>('/api/sessions', { template_id: w.id }).then((s) => nav(`/gym/${s.id}`))
                  }
                >
                  Start
                </Button>
                {activeProgram && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setAssignId(assignId === w.id ? null : w.id)
                      setAssignDay(0)
                    }}
                  >
                    Add to program
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => api.post(`/api/workouts/${w.id}/duplicate`).then(() => qc.invalidateQueries({ queryKey: ['workouts'] }))}
                >
                  Duplicate
                </Button>
              </div>
            </div>
            {assignId === w.id && activeProgram && (
              <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-line pt-3">
                <div className="min-w-40 flex-1">
                  <label className="mb-1 block text-xs uppercase tracking-wide text-muted">Day</label>
                  <Select value={assignDay} onChange={(e) => setAssignDay(Number(e.target.value))}>
                    {WEEKDAYS_FULL.map((day, i) => (
                      <option key={day} value={i}>{day}</option>
                    ))}
                  </Select>
                </div>
                <Button disabled={assigning} onClick={() => void addToProgram()}>
                  Add to {WEEKDAYS_FULL[assignDay]}
                </Button>
              </div>
            )}
          </div>
        ))}
        {data.length === 0 && <p className="text-muted">No workouts yet. Create one or generate a program.</p>}
      </div>
    </div>
  )
}

function emptySet(n: number): PrescribedSet {
  return {
    set_number: n,
    set_type: 'working',
    target_reps: 8,
    min_reps: 6,
    max_reps: 10,
    target_effort: 'medium',
    target_rpe: 7,
    rest_seconds: 90,
    target_weight: null,
    target_duration_seconds: null,
    target_distance_m: null,
    notes: null,
  }
}

export function WorkoutEditorPage() {
  const { id } = useParams()
  const nav = useNavigate()
  const qc = useQueryClient()
  const isNew = !id || id === 'new'
  const { data } = useQuery({
    queryKey: ['workout', id],
    queryFn: () => api.get<WorkoutTemplate>(`/api/workouts/${id}`),
    enabled: !isNew,
  })
  const [name, setName] = useState(data?.name || '')
  const [notes, setNotes] = useState(data?.notes || '')
  const [duration, setDuration] = useState(String(data?.estimated_duration_minutes || 45))
  const [exercises, setExercises] = useState<TemplateExercise[]>(data?.exercises || [])
  const [picker, setPicker] = useState<number | 'new' | null>(null)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    if (!isNew && data && !hydrated) {
      setName(data.name)
      setNotes(data.notes || '')
      setDuration(String(data.estimated_duration_minutes || 45))
      setExercises(data.exercises)
      setHydrated(true)
    }
  }, [data, isNew, hydrated])

  async function save() {
    const payload = {
      name,
      notes,
      estimated_duration_minutes: Number(duration) || null,
      exercises: exercises.map((ex, i) => ({
        exercise_id: ex.exercise_id,
        position: i,
        notes: ex.notes,
        rest_seconds: ex.rest_seconds,
        sets: ex.sets.map((s, si) => ({ ...s, set_number: si + 1 })),
      })),
    }
    const saved = isNew
      ? await api.post<WorkoutTemplate>('/api/workouts', payload)
      : await api.put<WorkoutTemplate>(`/api/workouts/${id}`, payload)
    void qc.invalidateQueries({ queryKey: ['workouts'] })
    void qc.invalidateQueries({ queryKey: ['workout', String(saved.id)] })
    void qc.invalidateQueries({ queryKey: ['programs'] })
    void qc.invalidateQueries({ queryKey: ['program-active'] })
    void qc.invalidateQueries({ queryKey: ['today'] })
    nav(`/workouts/${saved.id}`)
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 lg:px-8">
      <h1 className="mb-4 text-2xl font-semibold">{isNew ? 'New workout' : 'Edit workout'}</h1>
      <div className="space-y-4">
        <Field label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Estimated duration (min)">
          <Input value={duration} onChange={(e) => setDuration(e.target.value)} />
        </Field>
        <Field label="Notes">
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <div className="space-y-4">
          {exercises.map((ex, idx) => (
            <div key={`${ex.exercise_id}-${idx}`} className="rounded-xl border border-line bg-bg-raised p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{ex.exercise?.name || `Exercise ${ex.exercise_id}`}</div>
                  <div className="text-xs text-muted">{ex.exercise?.exercise_type}</div>
                </div>
                <div className="flex gap-2 text-xs">
                  <button onClick={() => setPicker(idx)}>Replace</button>
                  <button
                    onClick={() => setExercises(exercises.filter((_, i) => i !== idx))}
                    className="text-danger"
                  >
                    Remove
                  </button>
                  <button disabled={idx === 0} onClick={() => {
                    const next = [...exercises]
                    ;[next[idx - 1], next[idx]] = [next[idx], next[idx - 1]]
                    setExercises(next)
                  }}>Up</button>
                  <button disabled={idx === exercises.length - 1} onClick={() => {
                    const next = [...exercises]
                    ;[next[idx + 1], next[idx]] = [next[idx], next[idx + 1]]
                    setExercises(next)
                  }}>Down</button>
                </div>
              </div>
              {ex.exercise?.exercise_type === 'cardio' || ex.exercise?.exercise_type === 'timed' || ex.exercise?.exercise_type === 'distance' ? (
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Duration (sec)">
                    <Input
                      value={ex.sets[0]?.target_duration_seconds ?? 1200}
                      onChange={(e) => {
                        const next = [...exercises]
                        next[idx] = {
                          ...ex,
                          sets: [{ ...(ex.sets[0] || emptySet(1)), target_duration_seconds: Number(e.target.value) }],
                        }
                        setExercises(next)
                      }}
                    />
                  </Field>
                  <Field label="Effort">
                    <Input
                      value={ex.sets[0]?.target_effort ?? 'medium'}
                      onChange={(e) => {
                        const next = [...exercises]
                        next[idx] = {
                          ...ex,
                          sets: [{ ...(ex.sets[0] || emptySet(1)), target_effort: e.target.value }],
                        }
                        setExercises(next)
                      }}
                    />
                  </Field>
                </div>
              ) : (
                <div className="space-y-2">
                  {ex.sets.map((s, si) => (
                    <div key={si} className="grid grid-cols-6 gap-1 text-xs">
                      <Input value={s.set_type} onChange={(e) => {
                        const next = [...exercises]; const sets = [...ex.sets]; sets[si] = { ...s, set_type: e.target.value }; next[idx] = { ...ex, sets }; setExercises(next)
                      }} />
                      <Input placeholder="reps" value={s.target_reps ?? ''} onChange={(e) => {
                        const next = [...exercises]; const sets = [...ex.sets]; sets[si] = { ...s, target_reps: Number(e.target.value) }; next[idx] = { ...ex, sets }; setExercises(next)
                      }} />
                      <Input placeholder="min" value={s.min_reps ?? ''} onChange={(e) => {
                        const next = [...exercises]; const sets = [...ex.sets]; sets[si] = { ...s, min_reps: Number(e.target.value) }; next[idx] = { ...ex, sets }; setExercises(next)
                      }} />
                      <Input placeholder="max" value={s.max_reps ?? ''} onChange={(e) => {
                        const next = [...exercises]; const sets = [...ex.sets]; sets[si] = { ...s, max_reps: Number(e.target.value) }; next[idx] = { ...ex, sets }; setExercises(next)
                      }} />
                      <Input placeholder="RPE" value={s.target_rpe ?? ''} onChange={(e) => {
                        const next = [...exercises]; const sets = [...ex.sets]; sets[si] = { ...s, target_rpe: Number(e.target.value) }; next[idx] = { ...ex, sets }; setExercises(next)
                      }} />
                      <Input placeholder="rest" value={s.rest_seconds ?? ''} onChange={(e) => {
                        const next = [...exercises]; const sets = [...ex.sets]; sets[si] = { ...s, rest_seconds: Number(e.target.value) }; next[idx] = { ...ex, sets }; setExercises(next)
                      }} />
                    </div>
                  ))}
                  <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={() => {
                      const next = [...exercises]
                      next[idx] = { ...ex, sets: [...ex.sets, emptySet(ex.sets.length + 1)] }
                      setExercises(next)
                    }}>Add set</Button>
                    <Button size="sm" variant="ghost" onClick={() => {
                      const next = [...exercises]
                      next[idx] = { ...ex, sets: ex.sets.slice(0, -1) }
                      setExercises(next)
                    }}>Remove set</Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        <Button variant="secondary" onClick={() => setPicker('new')}>Add exercise</Button>
        <div className="flex gap-2">
          <Button onClick={() => void save()}>Save</Button>
          {!isNew && (
            <Button
              variant="danger"
              onClick={() => api.del(`/api/workouts/${id}`).then(() => nav('/workouts'))}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
      {picker !== null && (
        <ExercisePicker
          onClose={() => setPicker(null)}
          onSelect={(eid) => {
            api.get<Exercise>(`/api/exercises/${eid}`).then((exercise) => {
              const te: TemplateExercise = {
                exercise_id: eid,
                position: exercises.length,
                notes: null,
                rest_seconds: 90,
                exercise: exercise as never,
                sets: [emptySet(1), emptySet(2), emptySet(3)],
              }
              if (picker === 'new') setExercises([...exercises, te])
              else {
                const next = [...exercises]
                next[picker] = { ...te, position: picker }
                setExercises(next)
              }
              setPicker(null)
            })
          }}
        />
      )}
    </div>
  )
}
