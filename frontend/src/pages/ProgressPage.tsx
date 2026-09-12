import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '@/components/ui'
import { api } from '@/lib/api'

export function ProgressPage() {
  const [range, setRange] = useState('30d')
  const { data } = useQuery({
    queryKey: ['progress', range],
    queryFn: () => api.get<Record<string, unknown>>(`/api/analytics/progress?range=${range}`),
  })
  if (!data) return <div className="p-6 text-muted">Loading…</div>
  const body = data.body as { weight: { date: string; weight: number }[]; measurements: { date: string; waist: number }[] }
  const training = data.training as { volume: object[]; frequency: object[]; sets_per_muscle: { muscle: string; sets: number }[] }
  const cardio = data.cardio as object[]
  const nutrition = data.nutrition as object[]

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Progress</h1>
        <div className="flex gap-1">
          {['7d', '30d', '3m', '6m', '1y', 'all'].map((r) => (
            <button key={r} className={`rounded-full px-3 py-1 text-xs uppercase ${range === r ? 'bg-accent text-bg' : 'text-muted'}`} onClick={() => setRange(r)}>{r}</button>
          ))}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-medium">Weight</h2>
          {body.weight?.length ? <Mini data={body.weight} x="date" y="weight" /> : <p className="text-sm text-muted">No data yet.</p>}
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Training volume</h2>
          {training.volume?.length ? <MiniBar data={training.volume} x="date" y="volume" /> : <p className="text-sm text-muted">No data yet.</p>}
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Workout frequency</h2>
          {training.frequency?.length ? <MiniBar data={training.frequency} x="week" y="count" /> : <p className="text-sm text-muted">No data yet.</p>}
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Sets per muscle</h2>
          <ul className="text-sm">{training.sets_per_muscle?.map((m) => <li key={m.muscle} className="flex justify-between"><span>{m.muscle}</span><span className="tabular">{m.sets}</span></li>)}</ul>
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Cardio</h2>
          {cardio?.length ? <MiniBar data={cardio} x="week" y="duration" /> : <p className="text-sm text-muted">No cardio logged.</p>}
        </Card>
        <Card>
          <h2 className="mb-2 font-medium">Nutrition calories</h2>
          {nutrition?.length ? <Mini data={nutrition} x="date" y="calories" /> : <p className="text-sm text-muted">No nutrition logged.</p>}
        </Card>
      </div>
    </div>
  )
}

function Mini({ data, x, y }: { data: object[]; x: string; y: string }) {
  return (
    <div className="h-40">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <CartesianGrid stroke="#2a3440" vertical={false} />
          <XAxis dataKey={x} hide />
          <YAxis tick={{ fill: '#8b97a4', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#171d24', border: '1px solid #2a3440' }} />
          <Area type="monotone" dataKey={y} stroke="#3d9d8f" fill="#3d9d8f33" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function MiniBar({ data, x, y }: { data: object[]; x: string; y: string }) {
  return (
    <div className="h-40">
      <ResponsiveContainer>
        <BarChart data={data}>
          <XAxis dataKey={x} hide />
          <YAxis tick={{ fill: '#8b97a4', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#171d24', border: '1px solid #2a3440' }} />
          <Bar dataKey={y} fill="#3d9d8f" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
