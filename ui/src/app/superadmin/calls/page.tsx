import { Suspense } from 'react'
import { Metadata } from 'next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { 
  Phone, 
  PhoneCall, 
  Clock, 
  User, 
  Building2, 
  Play, 
  Flag, 
  Ban, 
  Trash2,
  Search,
  Download,
  Filter,
  ExternalLink
} from 'lucide-react'

export const metadata: Metadata = {
  title: 'Admin - All Calls | Dograh',
  description: 'Moderate and manage all platform calls'
}

// Mock data - replace with actual API calls
const mockCalls = [
  {
    id: 1001,
    started_at: '2024-01-15T10:30:00Z',
    caller: '+1234567890',
    callee: '+1987654321', 
    user: { id: 1, email: 'john@example.com', name: 'John Smith' },
    organization: { id: 1, name: 'Acme Corp' },
    status: 'completed',
    duration_seconds: 245,
    workflow: { id: 1, name: 'Sales Agent' },
    disposition: 'interested',
    recording_url: '/recordings/1001.mp3'
  },
  {
    id: 1002,
    started_at: '2024-01-15T11:15:00Z',
    caller: '+1234567891',
    callee: '+1987654322',
    user: { id: 2, email: 'jane@company.com', name: 'Jane Doe' },
    organization: { id: 2, name: 'TechStart Inc' },
    status: 'failed',
    duration_seconds: 67,
    workflow: { id: 2, name: 'Support Agent' },
    disposition: null,
    recording_url: null
  }
]

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

function CallsTable() {
  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search calls, users, organizations..."
              className="pl-10"
            />
          </div>
        </div>
        
        <Select defaultValue="all">
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="in_progress">In Progress</SelectItem>
          </SelectContent>
        </Select>

        <Select defaultValue="all">
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Direction</SelectItem>
            <SelectItem value="inbound">Inbound</SelectItem>
            <SelectItem value="outbound">Outbound</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm">
          <Filter className="h-4 w-4 mr-2" />
          More Filters
        </Button>

        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Calls Table */}
      <Card>
        <Table>
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
            {mockCalls.map((call) => (
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
                      <User className="h-4 w-4 text-gray-400" />
                      {call.user.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {call.user.email}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Building2 className="h-3 w-3" />
                      {call.organization.name}
                    </div>
                  </div>
                </TableCell>

                <TableCell>
                  <div className="space-y-2">
                    <CallStatusBadge status={call.status} />
                    {call.disposition && (
                      <div className="text-xs text-gray-500">
                        {call.disposition}
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
                      <a href={`/superadmin/calls/${call.id}`}>
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </Button>
                    <Button variant="ghost" size="sm" className="text-orange-600 hover:text-orange-700">
                      <Flag className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                      <Ban className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">
          Showing 1-2 of 234 calls
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
          <Button variant="outline" size="sm">
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function AdminCallsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">All Calls</h1>
          <p className="text-gray-500 mt-1">
            Monitor and moderate all platform calls
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <a href="/superadmin/calls/violations">
              <Flag className="h-4 w-4 mr-2" />
              View Violations (3)
            </a>
          </Button>
        </div>
      </div>

      <Suspense fallback={<div>Loading calls...</div>}>
        <CallsTable />
      </Suspense>
    </div>
  )
}
