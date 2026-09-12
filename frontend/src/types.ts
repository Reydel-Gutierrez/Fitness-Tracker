export type Profile = {
  user: { id: number; email: string; username: string; name: string; created_at: string }
  date_of_birth: string | null
  sex: string | null
  height: number | null
  primary_goal: string | null
  target_weight: number | null
  experience: string | null
  days_per_week: number | null
  preferred_days: number[]
  typical_duration_minutes: number | null
  available_locations: string[]
  available_equipment: string[]
  limitations: string | null
  weight_unit: string
  length_unit: string
  checkin_weekday: number
  onboarding_completed: boolean
  timezone: string | null
}

export type Exercise = {
  id: number
  name: string
  source: string
  exercise_type: string
  instructions: string[]
  primary_muscles: string[]
  secondary_muscles: string[]
  equipment: string[]
  difficulty: string | null
  category: string | null
  images: string[]
  thumbnail: string | null
  notes: string | null
  is_custom: boolean
}

export type PrescribedSet = {
  id?: number
  set_number: number
  set_type: string
  target_reps: number | null
  min_reps: number | null
  max_reps: number | null
  target_effort: string | null
  target_rpe: number | null
  rest_seconds: number | null
  target_weight: number | null
  target_duration_seconds: number | null
  target_distance_m: number | null
  notes: string | null
}

export type TemplateExercise = {
  id?: number
  exercise_id: number
  position: number
  notes: string | null
  rest_seconds: number | null
  exercise?: Exercise | null
  sets: PrescribedSet[]
}

export type WorkoutTemplate = {
  id: number
  name: string
  notes: string | null
  estimated_duration_minutes: number | null
  created_from: string
  exercises: TemplateExercise[]
}

export type PerformedSet = {
  id: number
  set_number: number
  set_type: string
  weight: number | null
  reps: number | null
  rpe: number | null
  added_weight: number | null
  assisted_weight: number | null
  completed: boolean
  skipped: boolean
  completed_at: string | null
  rest_seconds: number | null
  notes: string | null
  target_reps: number | null
  min_reps: number | null
  max_reps: number | null
  target_effort: string | null
  target_rpe: number | null
  target_weight: number | null
}

export type Cardio = {
  id: number
  duration_seconds: number | null
  distance_m: number | null
  calories: number | null
  avg_hr: number | null
  resistance: string | null
  rpe: number | null
  notes: string | null
  completed: boolean
  target_duration_seconds: number | null
  target_distance_m: number | null
  target_effort: string | null
  pace_sec_per_km: number | null
}

export type PerformedExercise = {
  id: number
  exercise_id: number
  position: number
  notes: string | null
  skipped: boolean
  exercise: Exercise | null
  sets: PerformedSet[]
  cardio: Cardio | null
  previous_date: string | null
  previous_sets: { set_number: number; weight: number | null; reps: number | null; rpe: number | null; completed: boolean }[]
  previous_cardio: Cardio | null
  suggestion: { id: number; suggested_weight: number | null; suggested_reps: number | null; reason: string; status: string } | null
}

export type WorkoutSession = {
  id: number
  name: string
  scheduled_date: string
  started_at: string | null
  completed_at: string | null
  status: string
  source: string
  notes: string | null
  duration_seconds: number | null
  template_id: number | null
  program_id: number | null
  exercises: PerformedExercise[]
  total_volume: number | null
  prs: string[]
}

export const GOALS = [
  { id: 'lose_fat', label: 'Lose fat' },
  { id: 'build_muscle', label: 'Build muscle' },
  { id: 'build_strength', label: 'Build strength' },
  { id: 'body_recomposition', label: 'Body recomposition' },
  { id: 'improve_endurance', label: 'Improve endurance' },
  { id: 'general_fitness', label: 'General fitness' },
]

export const EXPERIENCE = [
  { id: 'beginner', label: 'Beginner' },
  { id: 'intermediate', label: 'Intermediate' },
  { id: 'advanced', label: 'Advanced' },
]

export const EQUIPMENT = [
  'Gym',
  'Home',
  'Outdoor',
  'Peloton / stationary bike',
  'Barbell',
  'Dumbbells',
  'Machines',
  'Cable machines',
  'Pull-up bar',
  'Dip / parallel bars',
  'Bodyweight',
  'Running',
  'Other',
]

export const EXERCISE_TYPES = ['strength', 'bodyweight', 'cardio', 'timed', 'distance'] as const
