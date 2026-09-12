import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/hooks/useAuth'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage, RegisterPage } from '@/pages/AuthPages'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { TodayPage } from '@/pages/TodayPage'
import { WorkoutsPage, WorkoutEditorPage } from '@/features/workouts/WorkoutsPage'
import { GymPage } from '@/features/workouts/GymPage'
import { ProgramPage } from '@/pages/ProgramPage'
import { ExercisesPage, ExerciseFormPage, ExerciseDetailPage } from '@/pages/ExercisesPages'
import { BodyPage } from '@/pages/BodyPage'
import { NutritionPage } from '@/pages/NutritionPage'
import { ProgressPage } from '@/pages/ProgressPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { GoalsPage } from '@/pages/GoalsPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { CalendarPage, HistoryPage } from '@/pages/HistoryPage'

const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<AppShell />}>
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/" element={<DashboardPage />} />
              <Route path="/today" element={<TodayPage />} />
              <Route path="/workouts" element={<WorkoutsPage />} />
              <Route path="/workouts/calendar" element={<CalendarPage />} />
              <Route path="/workouts/new" element={<WorkoutEditorPage />} />
              <Route path="/workouts/:id" element={<WorkoutEditorPage />} />
              <Route path="/program" element={<ProgramPage />} />
              <Route path="/exercises" element={<ExercisesPage />} />
              <Route path="/exercises/new" element={<ExerciseFormPage />} />
              <Route path="/exercises/:id" element={<ExerciseDetailPage />} />
              <Route path="/body" element={<BodyPage />} />
              <Route path="/nutrition" element={<NutritionPage />} />
              <Route path="/progress" element={<ProgressPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/goals" element={<GoalsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/gym/:sessionId" element={<GymPage />} />
              <Route path="/history/:sessionId" element={<HistoryPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
