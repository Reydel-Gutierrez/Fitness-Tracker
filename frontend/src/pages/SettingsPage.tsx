import { useState } from 'react'
import { Button, Field } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'
import { api, getToken } from '@/lib/api'
import { WEEKDAYS_FULL } from '@/lib/utils'

export function SettingsPage() {
  const { profile, refresh, logout } = useAuth()
  const [weightUnit, setWeightUnit] = useState(profile?.weight_unit || 'lb')
  const [lengthUnit, setLengthUnit] = useState(profile?.length_unit || 'in')
  const [checkin, setCheckin] = useState(profile?.checkin_weekday ?? 4)

  async function save() {
    await api.put('/api/profile', { weight_unit: weightUnit, length_unit: lengthUnit, checkin_weekday: checkin })
    await refresh()
  }

  async function download(path: string, filename: string) {
    const res = await fetch(path, { headers: { Authorization: `Bearer ${getToken()}` } })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-6 lg:px-8">
      <h1 className="mb-4 text-2xl font-semibold">Settings</h1>
      <Field label="Weight unit">
        <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={weightUnit} onChange={(e) => setWeightUnit(e.target.value)}>
          <option value="lb">lb</option>
          <option value="kg">kg</option>
        </select>
      </Field>
      <div className="mt-3">
        <Field label="Length unit">
          <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={lengthUnit} onChange={(e) => setLengthUnit(e.target.value)}>
            <option value="in">inches</option>
            <option value="cm">cm</option>
          </select>
        </Field>
      </div>
      <div className="mt-3">
        <Field label="Check-in day">
          <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={checkin} onChange={(e) => setCheckin(Number(e.target.value))}>
            {WEEKDAYS_FULL.map((d, i) => <option key={d} value={i}>{d}</option>)}
          </select>
        </Field>
      </div>
      <Button className="mt-4" onClick={() => void save()}>Save</Button>
      <h2 className="mb-2 mt-8 font-medium">Export your data</h2>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => void download('/api/export/json', 'fitness.json')}>JSON</Button>
        <Button variant="secondary" onClick={() => void download('/api/export/measurements.csv', 'measurements.csv')}>Measurements CSV</Button>
        <Button variant="secondary" onClick={() => void download('/api/export/sets.csv', 'sets.csv')}>Sets CSV</Button>
        <Button variant="secondary" onClick={() => void download('/api/export/nutrition.csv', 'nutrition.csv')}>Nutrition CSV</Button>
        <Button variant="secondary" onClick={() => void download('/api/export/sessions.csv', 'sessions.csv')}>Sessions CSV</Button>
      </div>
      <Button className="mt-8" variant="danger" onClick={logout}>Sign out</Button>
    </div>
  )
}
