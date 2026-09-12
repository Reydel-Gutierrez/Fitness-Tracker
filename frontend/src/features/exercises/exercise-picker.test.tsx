import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ExercisePicker } from '@/features/exercises/ExercisePicker'
import { ExerciseImage } from '@/features/exercises/ExerciseImage'
import { api } from '@/lib/api'
import type { Exercise } from '@/types'

function sample(partial: Partial<Exercise> & Pick<Exercise, 'id' | 'name'>): Exercise {
  return {
    source: 'seed',
    exercise_type: 'strength',
    instructions: [],
    primary_muscles: ['quadriceps'],
    secondary_muscles: [],
    equipment: ['barbell'],
    difficulty: 'beginner',
    category: 'strength',
    images: [],
    thumbnail: null,
    notes: null,
    is_custom: false,
    ...partial,
  }
}

function renderPicker(exercises: Exercise[]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  vi.spyOn(api, 'get').mockImplementation(async (path: string) => {
    if (path.startsWith('/api/exercises/recent')) return []
    return exercises
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ExercisePicker onSelect={vi.fn()} onClose={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ExerciseImage', () => {
  it('uses a placeholder when the image is missing', () => {
    const { container } = render(<ExerciseImage src={null} alt="Missing" />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('svg')).toBeTruthy()
  })
})

describe('ExercisePicker', () => {
  it('shows compact searchable rows with muscle and equipment', async () => {
    const user = userEvent.setup()
    renderPicker([
      sample({ id: 1, name: 'Barbell Squat', thumbnail: '/media/exercises/thumbs/Barbell_Squat/0.jpg' }),
      sample({
        id: 2,
        name: 'Barbell Curl',
        primary_muscles: ['biceps'],
        thumbnail: '/media/exercises/thumbs/Barbell_Curl/0.jpg',
      }),
    ])
    expect(await screen.findByPlaceholderText('Search exercises...')).toBeInTheDocument()
    expect(await screen.findByText('Barbell Squat')).toBeInTheDocument()
    expect(screen.getByLabelText('All muscles')).toBeInTheDocument()
    expect(screen.getByLabelText('All equipment')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Strength' })).toBeInTheDocument()
    expect(screen.getByText('Quadriceps · Barbell')).toBeInTheDocument()
    const thumbs = document.querySelectorAll('img')
    expect(thumbs[0]).toHaveAttribute('src', '/media/exercises/thumbs/Barbell_Squat/0.jpg')
    expect(thumbs[0]).toHaveAttribute('loading', 'lazy')
    await user.type(screen.getByPlaceholderText('Search exercises...'), 'curl')
    expect(screen.getByText('Barbell Curl')).toBeInTheDocument()
    expect(screen.queryByText('Barbell Squat')).not.toBeInTheDocument()
  })
})
