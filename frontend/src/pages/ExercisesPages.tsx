import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { useState } from 'react'
import { Button, Field, Input, Textarea } from '@/components/ui'
import { api } from '@/lib/api'
import type { Exercise } from '@/types'
import { EXERCISE_TYPES } from '@/types'
import { ExerciseBrowser } from '@/features/exercises/ExercisePicker'
import { ExerciseImage } from '@/features/exercises/ExerciseImage'
import { titleCase } from '@/lib/utils'

function galleryThumb(src: string, thumbnail?: string | null, index?: number) {
  if (index === 0 && thumbnail) return thumbnail
  if (src.includes('/thumbs/')) return src
  return src.replace('/media/exercises/', '/media/exercises/thumbs/')
}

export function ExercisesPage() {
  return (
    <div className="mx-auto flex h-[calc(100svh-5rem)] max-w-4xl flex-col px-4 py-4 lg:h-svh lg:px-8 lg:py-6">
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <h1 className="text-2xl font-semibold">Exercises</h1>
        <Link to="/exercises/new" className="text-sm text-accent">
          New custom exercise
        </Link>
      </div>
      <ExerciseBrowser linkToDetail />
    </div>
  )
}

export function ExerciseFormPage() {
  const [name, setName] = useState('')
  const [type, setType] = useState('cardio')
  const [muscles, setMuscles] = useState('')
  const [equipment, setEquipment] = useState('')
  const [instructions, setInstructions] = useState('')
  const [notes, setNotes] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [savedId, setSavedId] = useState<number | null>(null)

  async function save() {
    const res = await api.post<Exercise>('/api/exercises', {
      name,
      exercise_type: type,
      primary_muscles: muscles.split(',').map((s) => s.trim()).filter(Boolean),
      equipment: equipment.split(',').map((s) => s.trim()).filter(Boolean),
      instructions,
      notes,
    })
    if (image) {
      const body = new FormData()
      body.append('file', image)
      await api.postForm(`/api/exercises/${res.id}/image`, body)
    }
    setSavedId(res.id)
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-6">
      <h1 className="mb-4 text-2xl font-semibold">Custom exercise</h1>
      <div className="space-y-3">
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Peloton Ride" /></Field>
        <Field label="Type">
          <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={type} onChange={(e) => setType(e.target.value)}>
            {EXERCISE_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Primary muscles (comma separated)"><Input value={muscles} onChange={(e) => setMuscles(e.target.value)} /></Field>
        <Field label="Equipment (comma separated)"><Input value={equipment} onChange={(e) => setEquipment(e.target.value)} /></Field>
        <Field label="Instructions"><Textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} /></Field>
        <Field label="Notes"><Textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <Field label="Image (optional)">
          <Input type="file" accept="image/*" onChange={(e) => setImage(e.target.files?.[0] ?? null)} />
        </Field>
        <Button onClick={() => void save()}>Save exercise</Button>
        {savedId && <p className="text-sm text-accent">Saved. <Link to={`/exercises/${savedId}`}>Open</Link></p>}
      </div>
    </div>
  )
}

export function ExerciseDetailPage() {
  const { id } = useParams()
  const [active, setActive] = useState(0)
  const { data } = useQuery({
    queryKey: ['exercise', id],
    queryFn: () => api.get<Exercise & { stats: { history: unknown[]; prs: { weight: number | null; e1rm: number | null } } }>(`/api/exercises/${id}`),
  })
  if (!data) return <div className="p-6 text-muted">Loading…</div>
  const images = data.images || []
  const current = images[Math.min(active, Math.max(images.length - 1, 0))] || null
  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-semibold">{data.name}</h1>
      <p className="text-sm text-muted">{titleCase(data.exercise_type)} · {data.difficulty} · {(data.equipment || []).map(titleCase).join(', ')}</p>
      <div className="mt-4">
        <ExerciseImage src={current} alt={data.name} variant="hero" />
        {images.length > 1 && (
          <div className="mt-2 flex gap-2 overflow-x-auto">
            {images.map((src, i) => (
              <button
                key={src}
                type="button"
                className={`shrink-0 rounded-md border ${i === active ? 'border-accent' : 'border-line'}`}
                onClick={() => setActive(i)}
              >
                <ExerciseImage src={galleryThumb(src, data.thumbnail, i)} alt="" size={56} className="h-14 w-14 rounded-md" />
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="mt-4 text-sm leading-relaxed">
        {(data.instructions || []).map((line, i) => <p key={i}>{line}</p>)}
      </div>
      <div className="mt-4 text-sm">
        <div>Primary: {(data.primary_muscles || []).map(titleCase).join(', ') || '—'}</div>
        <div>Secondary: {(data.secondary_muscles || []).map(titleCase).join(', ') || '—'}</div>
      </div>
      {data.stats && (
        <div className="mt-6 text-sm">
          <div>PR weight: {data.stats.prs?.weight ?? '—'}</div>
          <div>Est. 1RM: {data.stats.prs?.e1rm ?? '—'}</div>
        </div>
      )}
    </div>
  )
}
