import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Field, Input, Textarea } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/lib/api'
import { WEEKDAYS_FULL } from '@/lib/utils'
import { EQUIPMENT, EXPERIENCE, GOALS } from '@/types'

const LOCATIONS = ['Gym', 'Home', 'Outdoor', 'Peloton / stationary bike']

export function OnboardingPage() {
  const { profile, refresh } = useAuth()
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [name, setName] = useState(profile?.user.name || '')
  const [dob, setDob] = useState('')
  const [sex, setSex] = useState('')
  const [height, setHeight] = useState('')
  const [weight, setWeight] = useState('')
  const [bf, setBf] = useState('')
  const [goal, setGoal] = useState('general_fitness')
  const [targetWeight, setTargetWeight] = useState('')
  const [experience, setExperience] = useState('beginner')
  const [days, setDays] = useState(4)
  const [preferred, setPreferred] = useState<number[]>([0, 1, 3, 5])
  const [duration, setDuration] = useState(60)
  const [locations, setLocations] = useState<string[]>(['Gym'])
  const [equipment, setEquipment] = useState<string[]>(['Barbell', 'Dumbbells'])
  const [limitations, setLimitations] = useState('')
  const [weightUnit, setWeightUnit] = useState(profile?.weight_unit || 'lb')
  const [lengthUnit, setLengthUnit] = useState(profile?.length_unit || 'in')
  const [error, setError] = useState('')

  function toggle(list: string[], value: string, set: (v: string[]) => void) {
    set(list.includes(value) ? list.filter((x) => x !== value) : [...list, value])
  }

  async function finish() {
    setError('')
    try {
      await api.put('/api/profile', {
        name,
        date_of_birth: dob || null,
        sex: sex || null,
        height: height ? Number(height) : null,
        primary_goal: goal,
        target_weight: targetWeight ? Number(targetWeight) : null,
        experience,
        days_per_week: days,
        preferred_days: preferred,
        typical_duration_minutes: duration,
        available_locations: locations,
        available_equipment: equipment,
        limitations: limitations || null,
        weight_unit: weightUnit,
        length_unit: lengthUnit,
        onboarding_completed: true,
      })
      if (weight) {
        await api.post('/api/body', { weight: Number(weight), body_fat_pct: bf ? Number(bf) : null })
      }
      await refresh()
      nav('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save')
    }
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-8 lg:px-8">
      <p className="text-xs uppercase tracking-wide text-muted">Onboarding {step + 1} / 3</p>
      <h1 className="mb-6 mt-1 text-2xl font-semibold">Set up your log</h1>
      {step === 0 && (
        <div className="space-y-4">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Date of birth">
            <Input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
          </Field>
          <Field label="Sex (optional)">
            <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={sex} onChange={(e) => setSex(e.target.value)}>
              <option value="">Prefer not to say</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Weight unit">
              <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={weightUnit} onChange={(e) => setWeightUnit(e.target.value)}>
                <option value="lb">lb</option>
                <option value="kg">kg</option>
              </select>
            </Field>
            <Field label="Length unit">
              <select className="h-11 w-full rounded-lg border border-line bg-bg-raised px-3" value={lengthUnit} onChange={(e) => setLengthUnit(e.target.value)}>
                <option value="in">inches</option>
                <option value="cm">cm</option>
              </select>
            </Field>
          </div>
          <Field label={`Height (${lengthUnit})`}>
            <Input inputMode="decimal" value={height} onChange={(e) => setHeight(e.target.value)} />
          </Field>
          <Field label={`Current weight (${weightUnit})`}>
            <Input inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} />
          </Field>
          <Field label="Body fat % (optional)">
            <Input inputMode="decimal" value={bf} onChange={(e) => setBf(e.target.value)} />
          </Field>
        </div>
      )}
      {step === 1 && (
        <div className="space-y-4">
          <Field label="Primary goal">
            <div className="grid grid-cols-1 gap-2">
              {GOALS.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setGoal(g.id)}
                  className={`rounded-lg border px-3 py-3 text-left ${goal === g.id ? 'border-accent bg-accent/10' : 'border-line'}`}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </Field>
          <Field label={`Target weight (${weightUnit}, optional)`}>
            <Input inputMode="decimal" value={targetWeight} onChange={(e) => setTargetWeight(e.target.value)} />
          </Field>
          <Field label="Training experience">
            <div className="flex gap-2">
              {EXPERIENCE.map((x) => (
                <button
                  key={x.id}
                  type="button"
                  onClick={() => setExperience(x.id)}
                  className={`flex-1 rounded-lg border py-3 ${experience === x.id ? 'border-accent bg-accent/10' : 'border-line'}`}
                >
                  {x.label}
                </button>
              ))}
            </div>
          </Field>
        </div>
      )}
      {step === 2 && (
        <div className="space-y-4">
          <Field label="Days per week">
            <Input type="number" min={1} max={7} value={days} onChange={(e) => setDays(Number(e.target.value))} />
          </Field>
          <Field label="Preferred training days">
            <div className="flex flex-wrap gap-2">
              {WEEKDAYS_FULL.map((d, i) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setPreferred(preferred.includes(i) ? preferred.filter((x) => x !== i) : [...preferred, i])}
                  className={`rounded-full border px-3 py-2 text-sm ${preferred.includes(i) ? 'border-accent bg-accent/10' : 'border-line'}`}
                >
                  {d.slice(0, 3)}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Typical workout duration (minutes)">
            <Input type="number" value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
          </Field>
          <Field label="Locations">
            <div className="flex flex-wrap gap-2">
              {LOCATIONS.map((x) => (
                <button key={x} type="button" onClick={() => toggle(locations, x, setLocations)} className={`rounded-full border px-3 py-2 text-sm ${locations.includes(x) ? 'border-accent bg-accent/10' : 'border-line'}`}>
                  {x}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Equipment">
            <div className="flex flex-wrap gap-2">
              {EQUIPMENT.map((x) => (
                <button key={x} type="button" onClick={() => toggle(equipment, x, setEquipment)} className={`rounded-full border px-3 py-2 text-sm ${equipment.includes(x) ? 'border-accent bg-accent/10' : 'border-line'}`}>
                  {x}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Limitations or preferences (optional)">
            <Textarea value={limitations} onChange={(e) => setLimitations(e.target.value)} />
          </Field>
          <p className="text-xs text-muted">This is not medical advice. You control your own training and nutrition targets.</p>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
      <div className="mt-6 flex gap-3">
        {step > 0 && (
          <Button variant="secondary" onClick={() => setStep(step - 1)}>
            Back
          </Button>
        )}
        {step < 2 ? (
          <Button className="flex-1" onClick={() => setStep(step + 1)}>
            Continue
          </Button>
        ) : (
          <Button className="flex-1" onClick={() => void finish()}>
            Save and continue
          </Button>
        )}
      </div>
    </div>
  )
}
