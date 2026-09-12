import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Star } from 'lucide-react'
import { api } from '@/lib/api'
import { Button, Input } from '@/components/ui'
import { cn, titleCase } from '@/lib/utils'
import type { Exercise } from '@/types'
import { ExerciseImage } from '@/features/exercises/ExerciseImage'

const FAVORITES_KEY = 'ft_favorite_exercise_ids'
const ROW_PX = 48
const TYPE_FILTERS = [
  { id: '', label: 'All' },
  { id: 'strength', label: 'Strength' },
  { id: 'bodyweight', label: 'Bodyweight' },
  { id: 'cardio', label: 'Cardio' },
] as const

function readFavorites(): number[] {
  try {
    const raw = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]') as unknown
    return Array.isArray(raw) ? raw.filter((id): id is number => typeof id === 'number') : []
  } catch {
    return []
  }
}

function uniqueSorted(values: string[]) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b))
}

function matchesType(exercise: Exercise, type: string) {
  if (!type) return true
  if (type === 'cardio') return ['cardio', 'timed', 'distance'].includes(exercise.exercise_type)
  return exercise.exercise_type === type
}

export function ExerciseRow({
  exercise,
  onSelect,
  linkToDetail,
  favorite,
  onToggleFavorite,
}: {
  exercise: Exercise
  onSelect?: (id: number) => void
  linkToDetail?: boolean
  favorite: boolean
  onToggleFavorite: (id: number) => void
}) {
  const muscle = titleCase(exercise.primary_muscles?.[0]) || '—'
  const equipment = titleCase(exercise.equipment?.[0]) || '—'
  const body = (
    <>
      <ExerciseImage src={exercise.thumbnail} alt="" size={40} className="h-10 w-10 shrink-0 rounded-md" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium leading-tight">{exercise.name}</span>
        <span className="mt-0.5 block truncate text-xs text-muted">
          {muscle} · {equipment}
          <span className="text-muted/80"> · {titleCase(exercise.exercise_type)}</span>
        </span>
      </span>
    </>
  )
  const className = 'exercise-row flex h-12 min-w-0 flex-1 items-center gap-3 rounded-lg px-2 text-left hover:bg-bg-overlay'

  return (
    <div className="flex h-12 items-center gap-1">
      {linkToDetail ? (
        <Link to={`/exercises/${exercise.id}`} className={className}>
          {body}
        </Link>
      ) : (
        <button type="button" className={className} onClick={() => onSelect?.(exercise.id)}>
          {body}
        </button>
      )}
      <button
        type="button"
        className={cn('shrink-0 rounded-md p-2 text-muted hover:text-ink', favorite && 'text-accent')}
        aria-label={favorite ? 'Remove from favorites' : 'Add to favorites'}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          onToggleFavorite(exercise.id)
        }}
      >
        <Star size={14} fill={favorite ? 'currentColor' : 'none'} />
      </button>
    </div>
  )
}

function VirtualExerciseList({
  items,
  renderRow,
  header,
}: {
  items: Exercise[]
  renderRow: (exercise: Exercise) => ReactNode
  header?: ReactNode
}) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const headerRef = useRef<HTMLDivElement>(null)
  const [start, setStart] = useState(0)
  const [visible, setVisible] = useState(24)

  const update = useCallback(() => {
    const el = scrollerRef.current
    if (!el) return
    const headerH = headerRef.current?.offsetHeight ?? 0
    const adjusted = Math.max(0, el.scrollTop - headerH)
    const nextStart = Math.max(0, Math.floor(adjusted / ROW_PX) - 8)
    const nextVisible = Math.ceil(el.clientHeight / ROW_PX) + 16
    setStart((cur) => (cur === nextStart ? cur : nextStart))
    setVisible((cur) => (cur === nextVisible ? cur : nextVisible))
  }, [])

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    update()
    el.addEventListener('scroll', update, { passive: true })
    const Observer = typeof ResizeObserver === 'undefined' ? null : ResizeObserver
    const ro = Observer ? new Observer(update) : null
    if (ro) {
      ro.observe(el)
      if (headerRef.current) ro.observe(headerRef.current)
    }
    return () => {
      el.removeEventListener('scroll', update)
      ro?.disconnect()
    }
  }, [update, items.length])

  const end = Math.min(items.length, start + visible)
  const slice = items.slice(start, end)

  return (
    <div ref={scrollerRef} className="min-h-0 flex-1 overflow-auto">
      {header ? <div ref={headerRef}>{header}</div> : null}
      {items.length === 0 ? (
        <p className="px-2 py-6 text-sm text-muted">No exercises match those filters.</p>
      ) : (
        <div style={{ height: items.length * ROW_PX, position: 'relative' }}>
          <div style={{ position: 'absolute', top: start * ROW_PX, left: 0, right: 0 }}>
            {slice.map((exercise) => (
              <div key={exercise.id}>{renderRow(exercise)}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function ExerciseBrowser({
  onSelect,
  linkToDetail = false,
}: {
  onSelect?: (id: number) => void
  linkToDetail?: boolean
}) {
  const [q, setQ] = useState('')
  const [muscle, setMuscle] = useState('')
  const [equipment, setEquipment] = useState('')
  const [type, setType] = useState('')
  const [favoriteIds, setFavoriteIds] = useState<number[]>(readFavorites)

  const { data = [] } = useQuery({
    queryKey: ['exercises'],
    queryFn: () => api.get<Exercise[]>('/api/exercises'),
    staleTime: 60_000,
  })
  const { data: recent = [] } = useQuery({
    queryKey: ['exercises-recent'],
    queryFn: () => api.get<Exercise[]>('/api/exercises/recent'),
    staleTime: 30_000,
  })

  const muscles = useMemo(() => uniqueSorted(data.flatMap((ex) => ex.primary_muscles || [])), [data])
  const equipments = useMemo(() => uniqueSorted(data.flatMap((ex) => ex.equipment || [])), [data])
  const query = q.trim().toLowerCase()
  const filtering = Boolean(query || muscle || equipment || type)

  const filtered = useMemo(() => {
    return data.filter((ex) => {
      if (query && !ex.name.toLowerCase().includes(query) && !(ex.primary_muscles || []).some((m) => m.toLowerCase().includes(query))) {
        return false
      }
      if (muscle && !(ex.primary_muscles || []).map((m) => m.toLowerCase()).includes(muscle.toLowerCase()) && !(ex.secondary_muscles || []).map((m) => m.toLowerCase()).includes(muscle.toLowerCase())) {
        return false
      }
      if (equipment && !(ex.equipment || []).map((e) => e.toLowerCase()).includes(equipment.toLowerCase())) {
        return false
      }
      return matchesType(ex, type)
    })
  }, [data, query, muscle, equipment, type])

  const favorites = useMemo(
    () => favoriteIds.map((id) => data.find((ex) => ex.id === id)).filter((ex): ex is Exercise => Boolean(ex)),
    [data, favoriteIds],
  )

  function toggleFavorite(id: number) {
    setFavoriteIds((current) => {
      const next = current.includes(id) ? current.filter((item) => item !== id) : [id, ...current]
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(next))
      return next
    })
  }

  const favoriteSet = useMemo(() => new Set(favoriteIds), [favoriteIds])

  const row = (ex: Exercise) => (
    <ExerciseRow
      exercise={ex}
      onSelect={onSelect}
      linkToDetail={linkToDetail}
      favorite={favoriteSet.has(ex.id)}
      onToggleFavorite={toggleFavorite}
    />
  )

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 space-y-2 bg-bg pb-2">
        <Input placeholder="Search exercises..." value={q} onChange={(e) => setQ(e.target.value)} autoFocus={!linkToDetail} />
        <div className="flex gap-2">
          <select
            aria-label="All muscles"
            className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-bg-raised px-2 text-sm"
            value={muscle}
            onChange={(e) => setMuscle(e.target.value)}
          >
            <option value="">All muscles</option>
            {muscles.map((item) => (
              <option key={item} value={item}>
                {titleCase(item)}
              </option>
            ))}
          </select>
          <select
            aria-label="All equipment"
            className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-bg-raised px-2 text-sm"
            value={equipment}
            onChange={(e) => setEquipment(e.target.value)}
          >
            <option value="">All equipment</option>
            {equipments.map((item) => (
              <option key={item} value={item}>
                {titleCase(item)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-1 overflow-x-auto">
          {TYPE_FILTERS.map((item) => (
            <button
              key={item.id || 'all'}
              type="button"
              className={cn(
                'h-8 shrink-0 rounded-full border border-line px-3 text-xs',
                type === item.id ? 'bg-accent text-bg border-accent' : 'bg-bg-raised text-muted',
              )}
              onClick={() => setType(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <VirtualExerciseList
        items={filtered}
        renderRow={row}
        header={
          !filtering && (favorites.length > 0 || recent.length > 0) ? (
            <>
              {favorites.length > 0 && (
                <section className="pb-2">
                  <h3 className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted">Favorites</h3>
                  {favorites.slice(0, 8).map((ex) => (
                    <div key={`fav-${ex.id}`}>{row(ex)}</div>
                  ))}
                </section>
              )}
              {recent.length > 0 && (
                <section className="pb-2">
                  <h3 className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted">Recent</h3>
                  {recent.map((ex) => (
                    <div key={`recent-${ex.id}`}>{row(ex)}</div>
                  ))}
                </section>
              )}
              <h3 className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted">All exercises</h3>
            </>
          ) : null
        }
      />
    </div>
  )
}

export function ExercisePicker({
  onSelect,
  onClose,
}: {
  onSelect: (id: number) => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 sm:items-center sm:p-4" onClick={onClose}>
      <div
        className="flex h-[min(34rem,78svh)] w-full max-w-lg flex-col rounded-t-2xl border border-line bg-bg p-4 shadow-xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Choose exercise"
      >
        <div className="mb-3 flex shrink-0 items-center justify-between">
          <h2 className="text-lg font-semibold">Choose exercise</h2>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        <ExerciseBrowser onSelect={onSelect} />
      </div>
    </div>
  )
}
