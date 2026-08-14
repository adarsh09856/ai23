import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Play, Pause, Volume2, VolumeX } from 'lucide-react'

interface RecordingPlayerProps {
  url: string
  className?: string
}

export function RecordingPlayer({ url, className = '' }: RecordingPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [progress, setProgress] = useState(0)

  const togglePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const toggleMute = () => {
    setIsMuted(!isMuted)
  }

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  // Mock progress for demo - would be controlled by actual audio element
  const mockProgress = 35 // 35%
  const mockCurrentTime = 85 // 1:25
  const mockDuration = 245 // 4:05

  return (
    <div className={`flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg ${className}`}>
      {/* Play/Pause Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={togglePlayPause}
        className="shrink-0"
      >
        {isPlaying ? (
          <Pause className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4" />
        )}
      </Button>

      {/* Progress Bar */}
      <div className="flex-1 relative">
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-blue-500 transition-all duration-300 ease-out"
            style={{ width: `${mockProgress}%` }}
          />
        </div>
        
        {/* Invisible audio element would go here */}
        <audio className="hidden" />
      </div>

      {/* Time Display */}
      <div className="text-sm text-gray-500 font-mono shrink-0 min-w-[80px]">
        {formatTime(mockCurrentTime)} / {formatTime(mockDuration)}
      </div>

      {/* Mute Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={toggleMute}
        className="shrink-0 text-gray-500 hover:text-gray-700"
      >
        {isMuted ? (
          <VolumeX className="h-4 w-4" />
        ) : (
          <Volume2 className="h-4 w-4" />
        )}
      </Button>
    </div>
  )
}
