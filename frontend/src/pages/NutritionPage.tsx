import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Button, Card, Field, Input } from '@/components/ui'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'

type Day = {
  date: string
  entries: { id: number; meal: string; name: string; calories: number; protein_g: number; carbs_g: number; fat_g: number }[]
  totals: { calories: number; protein_g: number; carbs_g: number; fat_g: number }
  target: { calories: number; protein_g: number; carbs_g: number; fat_g: number }
}

type Food = { id: number; name: string; calories: number; protein_g: number; carbs_g: number; fat_g: number; serving_description: string }

const meals = ['breakfast', 'lunch', 'dinner', 'snack']

export function NutritionPage() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['nutrition-day'], queryFn: () => api.get<Day>('/api/nutrition/day') })
  const { data: foods = [] } = useQuery({ queryKey: ['foods'], queryFn: () => api.get<Food[]>('/api/nutrition/foods') })
  const [meal, setMeal] = useState('breakfast')
  const [name, setName] = useState('')
  const [cal, setCal] = useState('')
  const [pro, setPro] = useState('')
  const [carb, setCarb] = useState('')
  const [fat, setFat] = useState('')
  const [qty, setQty] = useState('1')
  const [targets, setTargets] = useState({ calories: '', protein_g: '', carbs_g: '', fat_g: '' })

  async function add() {
    await api.post('/api/nutrition/entries', {
      meal,
      name,
      quantity: Number(qty) || 1,
      calories: Number(cal) || 0,
      protein_g: Number(pro) || 0,
      carbs_g: Number(carb) || 0,
      fat_g: Number(fat) || 0,
    })
    setName(''); setCal(''); setPro(''); setCarb(''); setFat('')
    void qc.invalidateQueries({ queryKey: ['nutrition-day'] })
    void qc.invalidateQueries({ queryKey: ['foods'] })
  }

  useEffect(() => {
    if (data?.target) {
      setTargets({
        calories: String(data.target.calories),
        protein_g: String(data.target.protein_g),
        carbs_g: String(data.target.carbs_g),
        fat_g: String(data.target.fat_g),
      })
    }
  }, [data?.target])

  if (!data) return <div className="p-6 text-muted">Loading…</div>

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 lg:px-8">
      <h1 className="mb-4 text-2xl font-semibold">Nutrition</h1>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(['calories', 'protein_g', 'carbs_g', 'fat_g'] as const).map((k) => (
          <Card key={k}>
            <div className="text-xs uppercase text-muted">{k.replace('_g', '')}</div>
            <div className="text-lg tabular">{formatNumber(data.totals[k], 0)} / {formatNumber(data.target[k], 0)}</div>
          </Card>
        ))}
      </div>
      <div className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Field label="Meal">
          <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={meal} onChange={(e) => setMeal(e.target.value)}>
            {meals.map((m) => <option key={m}>{m}</option>)}
          </select>
        </Field>
        <Field label="Food"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Qty"><Input value={qty} onChange={(e) => setQty(e.target.value)} /></Field>
        <Field label="Calories"><Input inputMode="decimal" value={cal} onChange={(e) => setCal(e.target.value)} /></Field>
        <Field label="Protein"><Input inputMode="decimal" value={pro} onChange={(e) => setPro(e.target.value)} /></Field>
        <Field label="Carbs"><Input inputMode="decimal" value={carb} onChange={(e) => setCarb(e.target.value)} /></Field>
        <Field label="Fat"><Input inputMode="decimal" value={fat} onChange={(e) => setFat(e.target.value)} /></Field>
      </div>
      <Button onClick={() => void add()}>Log food</Button>
      {foods.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-xs uppercase text-muted">Frequent foods</div>
          <div className="flex flex-wrap gap-2">
            {foods.slice(0, 12).map((f) => (
              <button
                key={f.id}
                className="rounded-full border border-line px-3 py-1 text-sm"
                onClick={() => void api.post('/api/nutrition/entries', { meal, food_id: f.id, quantity: 1 }).then(() => qc.invalidateQueries({ queryKey: ['nutrition-day'] }))}
              >
                {f.name}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="mt-6 space-y-2">
        {data.entries.map((e) => (
          <div key={e.id} className="flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm">
            <span>{e.meal} · {e.name}</span>
            <span className="flex items-center gap-3">
              <span className="tabular">{formatNumber(e.calories, 0)} kcal · {formatNumber(e.protein_g, 0)} P</span>
              <button className="text-danger" onClick={() => void api.del(`/api/nutrition/entries/${e.id}`).then(() => qc.invalidateQueries({ queryKey: ['nutrition-day'] }))}>Delete</button>
            </span>
          </div>
        ))}
      </div>
      <h2 className="mb-2 mt-8 font-medium">Daily targets</h2>
      <p className="mb-3 text-xs text-muted">You set these. This is not medical nutrition advice.</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(['calories', 'protein_g', 'carbs_g', 'fat_g'] as const).map((k) => (
          <Input key={k} value={targets[k]} onChange={(e) => setTargets({ ...targets, [k]: e.target.value })} />
        ))}
      </div>
      <Button className="mt-3" variant="secondary" onClick={() => void api.put('/api/nutrition/target', {
        calories: Number(targets.calories), protein_g: Number(targets.protein_g), carbs_g: Number(targets.carbs_g), fat_g: Number(targets.fat_g),
      }).then(() => qc.invalidateQueries({ queryKey: ['nutrition-day'] }))}>Save targets</Button>
    </div>
  )
}
