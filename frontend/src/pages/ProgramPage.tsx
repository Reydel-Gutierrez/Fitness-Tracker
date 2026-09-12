import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, Select } from '@/components/ui'
import { api } from '@/lib/api'
import { WEEKDAYS_FULL, programWorkoutTitle } from '@/lib/utils'
import type { WorkoutTemplate } from '@/types'

type ProgramWorkout = {
  id: number
  weekday: number
  template_id: number
  name_override: string | null
  template: { id: number; name: string } | null
}

type Program = {
  id: number
  name: string
  notes: string | null
  generated: boolean
  is_active: boolean
  workouts: ProgramWorkout[]
}

export function ProgramPage() {
  const qc = useQueryClient()
  const nav = useNavigate()
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [addingDay, setAddingDay] = useState<number | null>(null)
  const [addTemplateId, setAddTemplateId] = useState<number | ''>('')
  const [adding, setAdding] = useState(false)
  const { data: active } = useQuery({ queryKey: ['program-active'], queryFn: () => api.get<Program | null>('/api/programs/active') })
  const { data: all = [] } = useQuery({ queryKey: ['programs'], queryFn: () => api.get<Program[]>('/api/programs') })
  const { data: templates = [] } = useQuery({ queryKey: ['workouts'], queryFn: () => api.get<WorkoutTemplate[]>('/api/workouts') })

  async function invalidateProgram() {
    void qc.invalidateQueries({ queryKey: ['programs'] })
    void qc.invalidateQueries({ queryKey: ['program-active'] })
    void qc.invalidateQueries({ queryKey: ['workouts'] })
    void qc.invalidateQueries({ queryKey: ['today'] })
  }

  async function persist(program: Program, workouts: ProgramWorkout[]) {
    await api.put(`/api/programs/${program.id}`, {
      name: program.name,
      notes: program.notes,
      is_active: program.is_active,
      workouts: workouts.map((w, i) => ({
        template_id: w.template_id,
        weekday: w.weekday,
        position: i,
        name_override: null,
      })),
    })
    await invalidateProgram()
  }

  async function generate() {
    const program = await api.post<Program>('/api/programs/generate')
    await invalidateProgram()
    nav('/program')
    return program
  }

  async function createBlank() {
    await api.post<Program>('/api/programs', { name: 'My program', notes: null, is_active: true, workouts: [] })
    await invalidateProgram()
  }

  async function remove(program: Program) {
    const count = program.workouts.length
    const ok = window.confirm(
      count
        ? `Delete "${program.name}" and its ${count} workout${count === 1 ? '' : 's'}? This cannot be undone.`
        : `Delete "${program.name}"? This cannot be undone.`,
    )
    if (!ok) return
    setDeletingId(program.id)
    try {
      await api.del(`/api/programs/${program.id}`)
      await invalidateProgram()
    } finally {
      setDeletingId(null)
    }
  }

  async function addToDay(weekday: number) {
    if (!active || addTemplateId === '') return
    setAdding(true)
    try {
      await persist(active, [
        ...active.workouts,
        {
          id: 0,
          weekday,
          template_id: Number(addTemplateId),
          name_override: null,
          template: templates.find((t) => t.id === Number(addTemplateId)) || null,
        },
      ])
      setAddTemplateId('')
      setAddingDay(null)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Program</h1>
        <div className="flex flex-wrap gap-2">
          {active && (
            <Button
              variant="danger"
              disabled={deletingId === active.id}
              onClick={() => void remove(active)}
            >
              Delete program
            </Button>
          )}
          {!active && <Button variant="secondary" onClick={() => void createBlank()}>New program</Button>}
          <Button onClick={() => void generate()}>Generate program</Button>
        </div>
      </div>
      {active ? (
        <Card className="mb-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-medium">{active.name}</h2>
              <p className="mt-1 text-sm text-muted">{active.notes}</p>
            </div>
            <Button
              size="sm"
              variant="danger"
              disabled={deletingId === active.id}
              onClick={() => void remove(active)}
            >
              Delete
            </Button>
          </div>
          <div className="mt-4 space-y-3">
            {WEEKDAYS_FULL.map((day, weekday) => {
              const items = active.workouts.filter((w) => w.weekday === weekday)
              const picking = addingDay === weekday
              return (
                <div key={day} className="rounded-lg border border-line p-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-medium">{day}</h3>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setAddingDay(picking ? null : weekday)
                        setAddTemplateId('')
                      }}
                    >
                      {picking ? 'Cancel' : 'Add workout'}
                    </Button>
                  </div>
                  <div className="mt-2 space-y-2">
                    {items.map((w) => (
                      <div key={w.id} className="flex items-center justify-between gap-2 rounded-md bg-bg-overlay px-3 py-2">
                        <Link to={`/workouts/${w.template_id}`} className="min-w-0 truncate font-medium">
                          {programWorkoutTitle(w)}
                        </Link>
                        <div className="flex shrink-0 gap-2">
                          <Button size="sm" variant="secondary" onClick={() => nav(`/workouts/${w.template_id}`)}>Edit</Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => void persist(active, active.workouts.filter((item) => item.id !== w.id))}
                          >
                            Remove
                          </Button>
                        </div>
                      </div>
                    ))}
                    {items.length === 0 && !picking && <p className="text-sm text-muted">Rest day</p>}
                    {picking && (
                      <div className="space-y-2 rounded-md border border-line p-3">
                        {templates.length === 0 ? (
                          <p className="text-sm text-muted">
                            Create a workout first (for example a Peloton ride), then add it to this day.{' '}
                            <Link to="/workouts/new" className="text-accent">New workout</Link>
                          </p>
                        ) : (
                          <>
                            <Select
                              value={addTemplateId}
                              onChange={(e) => setAddTemplateId(e.target.value ? Number(e.target.value) : '')}
                            >
                              <option value="">Choose a workout</option>
                              {templates.map((t) => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                              ))}
                            </Select>
                            <div className="flex flex-wrap items-center gap-2">
                              <Button disabled={addTemplateId === '' || adding} onClick={() => void addToDay(weekday)}>
                                Add to {day}
                              </Button>
                              <Link to="/workouts/new" className="text-sm text-accent">Create new workout</Link>
                            </div>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      ) : (
        <p className="text-muted">No active program. Generate one, or create a blank program and add workouts you already made.</p>
      )}
      {all.length > 0 && (
        <div>
          <h2 className="mb-2 font-medium">All programs</h2>
          {all.map((p) => (
            <div key={p.id} className="mb-2 flex items-center justify-between gap-3 rounded-lg border border-line bg-bg-raised px-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-sm">
                  {p.name} {p.is_active ? <span className="text-muted">(active)</span> : null}
                </div>
                <div className="text-xs text-muted">
                  {p.workouts.length} workout{p.workouts.length === 1 ? '' : 's'}
                </div>
              </div>
              <Button
                size="sm"
                variant="danger"
                disabled={deletingId === p.id}
                onClick={() => void remove(p)}
              >
                Delete
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
