import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Card, CardContent } from "@/components/ui/card"

interface TranscriptItem {
  speaker: string
  text: string
  timestamp: number
}

interface TranscriptViewerProps {
  transcript: TranscriptItem[]
  className?: string
}

export function TranscriptViewer({ transcript, className = '' }: TranscriptViewerProps) {
  const formatTimestamp = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  if (!transcript || transcript.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="text-center text-gray-500">
            No transcript available for this call
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {transcript.map((item, index) => (
        <div key={index} className="flex gap-3">
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback 
              className={
                item.speaker.toLowerCase().includes('assistant') || item.speaker.toLowerCase().includes('ai')
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' 
                  : 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
              }
            >
              {item.speaker.toLowerCase().includes('assistant') || item.speaker.toLowerCase().includes('ai') ? 'AI' : 'H'}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {item.speaker}
              </span>
              <span className="text-xs text-gray-400 font-mono">
                {formatTimestamp(item.timestamp)}
              </span>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
              {item.text}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
