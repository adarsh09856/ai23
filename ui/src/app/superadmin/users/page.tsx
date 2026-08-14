"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Eye, Search, UserCheck, UserX, Mail, Phone, Calendar } from "lucide-react";
import { toast } from "sonner";

interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  phone_number?: string;
  organization?: {
    id: number;
    name: string;
  };
  _stats?: {
    total_calls: number;
    total_minutes: number;
    last_activity?: string;
  };
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/admin/users", {
        credentials: "include"
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      } else {
        toast.error("Failed to load users");
      }
    } catch (error) {
      console.error("Failed to load users:", error);
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  const toggleUserStatus = async (userId: number, newStatus: boolean) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ is_active: newStatus })
      });

      if (response.ok) {
        await loadUsers(); // Reload data
        toast.success(`User ${newStatus ? 'activated' : 'deactivated'} successfully`);
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to update user");
      }
    } catch (error) {
      console.error("Failed to update user:", error);
      toast.error("Failed to update user");
    }
  };

  const filteredUsers = users.filter(user => 
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.organization?.name || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const UserDetailsModal = ({ user }: { user: User }) => (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Eye className="h-5 w-5" />
          User Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <Label className="text-sm font-medium text-muted-foreground">Email</Label>
            <p className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              {user.email}
            </p>
          </div>
          
          <div>
            <Label className="text-sm font-medium text-muted-foreground">Status</Label>
            <p>
              <Badge variant={user.is_active ? "default" : "destructive"}>
                {user.is_active ? "Active" : "Inactive"}
              </Badge>
            </p>
          </div>

          <div>
            <Label className="text-sm font-medium text-muted-foreground">Organization</Label>
            <p>{user.organization?.name || "No organization"}</p>
          </div>

          <div>
            <Label className="text-sm font-medium text-muted-foreground">Phone</Label>
            <p className="flex items-center gap-2">
              <Phone className="h-4 w-4" />
              {user.phone_number || "Not provided"}
            </p>
          </div>

          <div>
            <Label className="text-sm font-medium text-muted-foreground">Joined</Label>
            <p className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              {formatDate(user.created_at)}
            </p>
          </div>

          <div>
            <Label className="text-sm font-medium text-muted-foreground">Last Activity</Label>
            <p>{user._stats?.last_activity ? formatDate(user._stats.last_activity) : "Never"}</p>
          </div>
        </div>

        {user._stats && (
          <div className="pt-4 border-t">
            <h4 className="font-medium mb-2">Usage Statistics</h4>
            <div className="grid gap-2 md:grid-cols-3">
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{user._stats.total_calls}</div>
                <div className="text-sm text-muted-foreground">Total Calls</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{Math.round(user._stats.total_minutes)}</div>
                <div className="text-sm text-muted-foreground">Total Minutes</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">
                  {user._stats.total_calls > 0 ? (user._stats.total_minutes / user._stats.total_calls).toFixed(1) : "0"}
                </div>
                <div className="text-sm text-muted-foreground">Avg Minutes/Call</div>
              </div>
            </div>
          </div>
        )}

        <div className="flex gap-2 pt-4">
          <Button
            variant={user.is_active ? "destructive" : "default"}
            onClick={() => toggleUserStatus(user.id, !user.is_active)}
          >
            {user.is_active ? (
              <>
                <UserX className="mr-2 h-4 w-4" />
                Deactivate User
              </>
            ) : (
              <>
                <UserCheck className="mr-2 h-4 w-4" />
                Activate User
              </>
            )}
          </Button>
          <Button variant="outline" onClick={() => setSelectedUser(null)}>
            Close
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">User Management</h1>
          <p className="text-muted-foreground">
            View and manage platform users and their activity.
          </p>
        </div>
        <Badge variant="secondary" className="text-lg px-3 py-1">
          {users.length} Total Users
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search users by email or organization..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredUsers.map((user) => (
              <div key={user.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <div>
                      <h3 className="font-medium">{user.email}</h3>
                      <p className="text-sm text-muted-foreground">
                        {user.organization?.name || "No organization"} • 
                        Joined {formatDate(user.created_at)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {user._stats && (
                    <div className="text-right text-sm">
                      <div>{user._stats.total_calls} calls</div>
                      <div className="text-muted-foreground">{Math.round(user._stats.total_minutes)} min</div>
                    </div>
                  )}
                  
                  <Badge variant={user.is_active ? "default" : "destructive"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedUser(user)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Details
                  </Button>
                </div>
              </div>
            ))}

            {filteredUsers.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No users found matching your search.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {selectedUser && <UserDetailsModal user={selectedUser} />}
    </div>
  );
}
