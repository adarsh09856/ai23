import { Suspense } from 'react'
import { Metadata } from 'next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { 
  Flag, 
  AlertTriangle, 
  Ban, 
  CheckCircle, 
  X, 
  Eye,
  Search,
  Filter,
  ArrowLeft,
  User,
  Building2,
  Calendar,
  MessageSquare
} from 'lucide-react'

export const metadata: Metadata = {
  title: 'Violations Queue | Admin - Dograh',
  description: 'Review and moderate flagged calls and content violations'
}

// Mock violations data
const mockViolations = [
  {
    id: 1,
    call_id: 1001,
    call_timestamp: '2024-01-15T10:30:00Z',
    user: { id: 1, email: 'user1@example.com' },
    org: { id: 1, name: 'Acme Corp' },
    detected_phrase: 'inappropriate language detected',
    severity: 'high',
    status: 'pending',
    reviewed_by: null,
    reviewed_at: null
  },
  {
    id: 2,
    call_id: 1002,
    call_timestamp: '2024-01-15T11:15:00Z',
    user: { id: 2, email: 'user2@company.com' },
    org: { id: 2, name: 'TechStart Inc' },
    detected_phrase: 'Admin flagged: Suspicious activity pattern',
    severity: 'critical',
    status: 'reviewed',
    reviewed_by: { id: 1, email: 'admin@admin.com' },
    reviewed_at: '2024-01-15T12:00:00Z'
  },
  {
    id: 3,
    call_id: 1003,
    call_timestamp: '2024-01-15T14:20:00Z',
    user: { id: 3, email: 'user3@business.com' },
    org: { id: 1, name: 'Acme Corp' },
    detected_phrase: 'spam keywords detected',
    severity: 'medium',
    status: 'dismissed',
    reviewed_by: { id: 1, email: 'admin@admin.com' },
    reviewed_at: '2024-01-15T15:30:00Z'
  }
]

function SeverityBadge({ severity }: { severity: string }) {
  const variants = {
    low: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    medium: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
    high: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    critical: 'bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-100 font-semibold'
  }
  
  return (
    <Badge className={variants[severity as keyof typeof variants]}>
      {severity.toUpperCase()}
    </Badge>
  )
}

function StatusBadge({ status }: { status: string }) {
  const variants = {
    pending: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    reviewed: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300',
    actioned: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    dismissed: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
  }
  
  const icons = {
    pending: <AlertTriangle className="h-3 w-3" />,
    reviewed: <Eye className="h-3 w-3" />,
    actioned: <CheckCircle className="h-3 w-3" />,
    dismissed: <X className="h-3 w-3" />
  }
  
  return (
    <Badge className={`${variants[status as keyof typeof variants]} flex items-center gap-1`}>
      {icons[status as keyof typeof icons]}
      {status}
    </Badge>
  )
}

function ViolationsTable() {
  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search violations, users, phrases..."
              className="pl-10"
            />
          </div>
        </div>
        
        <Select defaultValue="all">
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severity</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>

        <Select defaultValue="pending">
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="reviewed">Reviewed</SelectItem>
            <SelectItem value="actioned">Actioned</SelectItem>
            <SelectItem value="dismissed">Dismissed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Bulk Actions */}
      <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
        <Checkbox id="select-all" />
        <label htmlFor="select-all" className="text-sm font-medium">
          Select All
        </label>
        <div className="flex-1"></div>
        <Button variant="outline" size="sm" disabled>
          <CheckCircle className="h-4 w-4 mr-2" />
          Mark Reviewed
        </Button>
        <Button variant="outline" size="sm" disabled>
          <X className="h-4 w-4 mr-2" />
          Dismiss Selected
        </Button>
        <Button variant="destructive" size="sm" disabled>
          <Ban className="h-4 w-4 mr-2" />
          Ban Users
        </Button>
      </div>

      {/* Violations Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox />
              </TableHead>
              <TableHead>Violation</TableHead>
              <TableHead>Call Info</TableHead>
              <TableHead>User/Organization</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Reviewed</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockViolations.map((violation) => (
              <TableRow key={violation.id}>
                <TableCell>
                  <Checkbox />
                </TableCell>
                
                <TableCell>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Flag className="h-4 w-4 text-red-500" />
                      <span className="text-sm font-medium">Violation #{violation.id}</span>
                    </div>
                    <div className="text-xs text-gray-600 max-w-xs truncate">
                      {violation.detected_phrase}
                    </div>
                    <div className="text-xs text-gray-400">
                      {new Date(violation.call_timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </TableCell>

                <TableCell>
                  <div className="space-y-1">
                    <Button variant="link" size="sm" className="p-0 h-auto" asChild>
                      <a href={`/superadmin/calls/${violation.call_id}`}>
                        Call #{violation.call_id}
                      </a>
                    </Button>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Calendar className="h-3 w-3" />
                      {new Date(violation.call_timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </TableCell>

                <TableCell>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm">
                      <User className="h-4 w-4 text-gray-400" />
                      {violation.user.email}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Building2 className="h-3 w-3" />
                      {violation.org.name}
                    </div>
                  </div>
                </TableCell>

                <TableCell>
                  <SeverityBadge severity={violation.severity} />
                </TableCell>

                <TableCell>
                  <StatusBadge status={violation.status} />
                </TableCell>

                <TableCell>
                  {violation.reviewed_by ? (
                    <div className="space-y-1">
                      <div className="text-sm text-gray-600">
                        {violation.reviewed_by.email}
                      </div>
                      <div className="text-xs text-gray-400">
                        {new Date(violation.reviewed_at!).toLocaleDateString()}
                      </div>
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400">Not reviewed</span>
                  )}
                </TableCell>

                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" asChild>
                      <a href={`/superadmin/calls/${violation.call_id}`}>
                        <Eye className="h-4 w-4" />
                      </a>
                    </Button>
                    
                    {violation.status === 'pending' && (
                      <>
                        <Button variant="ghost" size="sm" className="text-green-600 hover:text-green-700">
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" className="text-gray-600 hover:text-gray-700">
                          <X className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                          <Ban className="h-4 w-4" />
                        </Button>
                      </>
                    )}
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
          Showing 3 of 12 violations
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

export default function ViolationsQueuePage() {
  const pendingCount = mockViolations.filter(v => v.status === 'pending').length
  const criticalCount = mockViolations.filter(v => v.severity === 'critical').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <a href="/superadmin/calls">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Calls
            </a>
          </Button>
          
          <div>
            <h1 className="text-3xl font-bold">Violations Queue</h1>
            <p className="text-gray-500 mt-1">
              Review flagged calls and content violations
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div>
                <p className="text-2xl font-bold text-blue-600">{pendingCount}</p>
                <p className="text-sm text-gray-500">Pending Review</p>
              </div>
              <AlertTriangle className="ml-auto h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div>
                <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
                <p className="text-sm text-gray-500">Critical Severity</p>
              </div>
              <Flag className="ml-auto h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div>
                <p className="text-2xl font-bold text-green-600">15</p>
                <p className="text-sm text-gray-500">Resolved Today</p>
              </div>
              <CheckCircle className="ml-auto h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div>
                <p className="text-2xl font-bold text-orange-600">5.2%</p>
                <p className="text-sm text-gray-500">Violation Rate</p>
              </div>
              <MessageSquare className="ml-auto h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Suspense fallback={<div>Loading violations...</div>}>
        <ViolationsTable />
      </Suspense>
    </div>
  )
}
