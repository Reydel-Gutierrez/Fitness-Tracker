import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

function SetRow({ onComplete }: { onComplete: (reps: number) => void }) {
  return (
    <div>
      <input aria-label="Reps" defaultValue={7} />
      <button onClick={() => onComplete(7)}>COMPLETE SET</button>
    </div>
  )
}

describe('complete set control', () => {
  it('records the performed reps when completing a set', async () => {
    const user = userEvent.setup()
    let saved: number | null = null
    render(<SetRow onComplete={(reps) => { saved = reps }} />)
    await user.click(screen.getByRole('button', { name: 'COMPLETE SET' }))
    expect(saved).toBe(7)
  })
})
