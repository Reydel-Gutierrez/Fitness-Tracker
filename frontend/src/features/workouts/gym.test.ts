import { remainingSeconds } from '@/features/workouts/GymPage'

describe('rest timer', () => {
  it('uses timestamps so tab backgrounding does not drift', () => {
    const endsAt = 10_000
    expect(remainingSeconds(endsAt, 7_200)).toBe(3)
    expect(remainingSeconds(endsAt, 10_500)).toBe(0)
  })
})
