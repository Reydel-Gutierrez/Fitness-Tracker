import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Field, Input } from '@/components/ui'
import { useAuth } from '@/hooks/useAuth'

export function LoginPage() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const profile = await login(email, password)
      nav(profile.onboarding_completed ? '/' : '/onboarding')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-md flex-col justify-center px-6">
      <h1 className="mb-1 text-2xl font-semibold">Fitness Tracker</h1>
      <p className="mb-8 text-sm text-muted">Sign in to continue training.</p>
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password">
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button className="w-full" size="lg" type="submit">
          Sign in
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted">
        New here? <Link to="/register" className="text-accent">Create an account</Link>
      </p>
    </div>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await register(name, email, password)
      nav('/onboarding')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not register')
    }
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-md flex-col justify-center px-6">
      <h1 className="mb-1 text-2xl font-semibold">Create account</h1>
      <p className="mb-8 text-sm text-muted">Local authentication. Your data stays on this server.</p>
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Email">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password">
          <Input type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button className="w-full" size="lg" type="submit">
          Create account
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted">
        Already have an account? <Link to="/login" className="text-accent">Sign in</Link>
      </p>
    </div>
  )
}
