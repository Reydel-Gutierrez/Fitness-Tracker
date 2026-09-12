import { useState } from 'react'
import { Dumbbell } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ExerciseImage({
  src,
  alt,
  className,
  size = 40,
  variant = 'thumb',
}: {
  src?: string | null
  alt: string
  className?: string
  size?: number
  variant?: 'thumb' | 'hero'
}) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null)
  const placeholder = !src || failedSrc === src
  if (placeholder) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-bg-overlay text-muted',
          variant === 'hero' && 'aspect-[4/3] w-full rounded-xl',
          className,
        )}
        style={variant === 'thumb' ? { width: size, height: size } : undefined}
        aria-hidden={!alt}
      >
        <Dumbbell size={variant === 'hero' ? 40 : Math.max(14, Math.round(size * 0.45))} />
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      width={variant === 'thumb' ? size : undefined}
      height={variant === 'thumb' ? size : undefined}
      loading="lazy"
      decoding="async"
      sizes={variant === 'thumb' ? `${size}px` : '(max-width: 768px) 100vw, 640px'}
      className={cn('bg-bg-overlay object-cover', variant === 'hero' && 'max-h-80 w-full rounded-xl object-contain', className)}
      onError={() => setFailedSrc(src)}
    />
  )
}
