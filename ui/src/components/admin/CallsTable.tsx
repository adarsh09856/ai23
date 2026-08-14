import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { 
  PhoneCall, 
  Clock, 
  User, 
  Building2, 
  Play, 
  Flag, 
  Ban, 
  Trash2,
  ExternalLink
} from 'lucide-react'

interface CallItem {
  id: number
  started_at: string
  caller: string
  callee: string
  user: {
    id: number
    email: string
    name: string
  }
  organization: {
    id: number
    name: string
  }
  status: string
  duration_seconds: number | null
  workflow: {
    id: number
    name: string
  }
  disposition: string | null
  recording_url: string | null
}

interface CallsTableProps {
  calls: CallItem[]
  onBanUser?: (callId: number, userId: number) => void
  onFlagCall?: (callId: number) => void
  onDeleteCall?: (callId: number) => void
  className?: string
}

function CallStatusBadge({ status }: { status: string }) {
  const variants = {
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
  }
  
  return (
    <Badge className={variants[status as keyof typeof variants] || variants.completed}>
      {status.replace('_', ' ')}
    </Badge>
  )
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '0s'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
}

export function CallsTable({ 
  calls, 
  onBanUser, 
  onFlagCall, 
  onDeleteCall, 
  className = '' 
}: CallsTableProps) {
  return (
    <Table className={className}>
      <TableHeader>
        <TableRow>
          <TableHead>Call Info</TableHead>
          <TableHead>User/Organization</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Duration</TableHead>
          <TableHead>Workflow</TableHead>
          <TableHead>Recording</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {calls.map((call) => (
          <TableRow key={call.id}>
            <TableCell>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <PhoneCall className="h-4 w-4 text-blue-500" />
                  Call #{call.id}
                </div>
                <div className="text-xs text-gray-500">
                  {call.caller} → {call.callee}
                </div>
                <div className="text-xs text-gray-400">
                  {new Date(call.started_at).toLocaleString()}
                </div>
              </div>
            </TableCell>
            
            <TableCell>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm">
                  <Avatar className="h-5 w-5">
                    <AvatarFallback className="text-xs">
                      {call.user.name.split(' ').map(n => n[0]).join('').toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  {call.user.name}
                </div>
                <div className="text-xs text-gray-500 ml-7">
                  {call.user.email}
                </div>
                <div className="flex items-center gap-1 text-xs text-gray-400 ml-7">
                  <Building2 className="h-3 w-3" />
                  {call.organization.name}
                </div>
              </div>
            </TableCell>

            <TableCell>
              <div className="space-y-2">
                <CallStatusBadge status={call.status} />
                {call.disposition && (
                  <div className="text-xs text-gray-500 capitalize">
                    {call.disposition.replace('_', ' ')}
                  </div>
                )}
              </div>
            </TableCell>

            <TableCell>
              <div className="flex items-center gap-1 text-sm">
                <Clock className="h-4 w-4 text-gray-400" />
                {formatDuration(call.duration_seconds)}
              </div>
            </TableCell>

            <TableCell>
              <div className="text-sm">
                {call.workflow.name}
              </div>
            </TableCell>

            <TableCell>
              {call.recording_url ? (
                <Button variant="outline" size="sm">
                  <Play className="h-4 w-4 mr-2" />
                  Play
                </Button>
              ) : (
                <span className="text-xs text-gray-400">No recording</span>
              )}
            </TableCell>

            <TableCell>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" asChild>
                  <a href={`/superadmin/calls/${call.id}`} title="View Details">
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </Button>
                
                {onFlagCall && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-orange-600 hover:text-orange-700"
                    onClick={() => onFlagCall(call.id)}
                    title="Flag Call"
                  >
                    <Flag className="h-4 w-4" />
                  </Button>
                )}
                
                {onBanUser && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-red-600 hover:text-red-700"
                    onClick={() => onBanUser(call.id, call.user.id)}
                    title="Ban User"
                  >
                    <Ban className="h-4 w-4" />
                  </Button>
                )}
                
                {onDeleteCall && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-red-600 hover:text-red-700"
                    onClick={() => onDeleteCall(call.id)}
                    title="Delete Call"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
