"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Eye, Search, Users, Phone, Settings, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface Organization {
  id: number;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  phone_number?: string;
  _stats?: {
    user_count: number;
    total_calls: number;
    total_minutes: number;
    active_workflows: number;
    last_activity?: string;
  };
}

export default function OrganizationsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/admin/organizations", {
        credentials: "include"
      });

      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      } else {
        toast.error("Failed to load organizations");
      }
    } catch (error) {
      console.error("Failed to load organizations:", error);
      toast.error("Failed to load organizations");
    } finally {
      setLoading(false);
    }
  };

  const toggleOrgStatus = async (orgId: number, newStatus: boolean) => {
    try {
      const response = await fetch(`/api/admin/organizations/${orgId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ is_active: newStatus })
      });

      if (response.ok) {
        await loadOrganizations();
        toast.success(`Organization ${newStatus ? 'activated' : 'deactivated'} successfully`);
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to update organization");
      }
    } catch (error) {
      console.error("Failed to update organization:", error);
      toast.error("Failed to update organization");
    }
  };

  const deleteOrganization = async (orgId: number) => {
    if (!confirm("Are you sure? This will permanently delete the organization and all its data.")) {
      return;
    }

    try {
      const response = await fetch(`/api/admin/organizations/${orgId}`, {
        method: "DELETE",
        credentials: "include"
      });

      if (response.ok) {
        await loadOrganizations();
        setSelectedOrg(null);
        toast.success("Organization deleted successfully");
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to delete organization");
      }
    } catch (error) {
      console.error("Failed to delete organization:", error);
      toast.error("Failed to delete organization");
    }
  };

  const filteredOrgs = organizations.filter(org => 
    org.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const OrganizationDetailsModal = ({ org }: { org: Organization }) => (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Eye className="h-5 w-5" />
          Organization Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-muted-foreground">Organization Name</label>
            <p className="text-lg font-medium">{org.name}</p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-muted-foreground">Status</label>
            <p>
              <Badge variant={org.is_active ? "default" : "destructive"}>
                {org.is_active ? "Active" : "Inactive"}
              </Badge>
            </p>
          </div>

          <div>
            <label className="text-sm font-medium text-muted-foreground">Phone</label>
            <p className="flex items-center gap-2">
              <Phone className="h-4 w-4" />
              {org.phone_number || "Not provided"}
            </p>
          </div>

          <div>
            <label className="text-sm font-medium text-muted-foreground">Created</label>
            <p>{formatDate(org.created_at)}</p>
          </div>

          <div>
            <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
            <p>{formatDate(org.updated_at)}</p>
          </div>

          <div>
            <label className="text-sm font-medium text-muted-foreground">Last Activity</label>
            <p>{org._stats?.last_activity ? formatDate(org._stats.last_activity) : "Never"}</p>
          </div>
        </div>

        {org._stats && (
          <div className="pt-4 border-t">
            <h4 className="font-medium mb-4">Organization Statistics</h4>
            <div className="grid gap-4 md:grid-cols-4">
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-bold flex items-center justify-center gap-2">
                  <Users className="h-6 w-6" />
                  {org._stats.user_count}
                </div>
                <div className="text-sm text-muted-foreground">Users</div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{org._stats.total_calls}</div>
                <div className="text-sm text-muted-foreground">Total Calls</div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{Math.round(org._stats.total_minutes)}</div>
                <div className="text-sm text-muted-foreground">Total Minutes</div>
              </div>
              <div className="text-center p-4 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{org._stats.active_workflows}</div>
                <div className="text-sm text-muted-foreground">Active Workflows</div>
              </div>
            </div>
            
            {org._stats.total_calls > 0 && (
              <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg">
                <div className="text-center">
                  <div className="text-xl font-bold">
                    {(org._stats.total_minutes / org._stats.total_calls).toFixed(1)} min
                  </div>
                  <div className="text-sm text-muted-foreground">Average Call Duration</div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 pt-4">
          <Button
            variant={org.is_active ? "destructive" : "default"}
            onClick={() => toggleOrgStatus(org.id, !org.is_active)}
          >
            <Settings className="mr-2 h-4 w-4" />
            {org.is_active ? "Deactivate" : "Activate"}
          </Button>
          
          <Button
            variant="destructive"
            onClick={() => deleteOrganization(org.id)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete Organization
          </Button>
          
          <Button variant="outline" onClick={() => setSelectedOrg(null)}>
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
          <h1 className="text-3xl font-bold">Organization Management</h1>
          <p className="text-muted-foreground">
            View and manage platform organizations and their activity.
          </p>
        </div>
        <Badge variant="secondary" className="text-lg px-3 py-1">
          {organizations.length} Total Organizations
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search organizations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredOrgs.map((org) => (
              <div key={org.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <div>
                      <h3 className="font-medium">{org.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        Created {formatDate(org.created_at)}
                        {org._stats && ` • ${org._stats.user_count} users`}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {org._stats && (
                    <div className="text-right text-sm">
                      <div>{org._stats.total_calls} calls</div>
                      <div className="text-muted-foreground">{Math.round(org._stats.total_minutes)} min</div>
                    </div>
                  )}
                  
                  <Badge variant={org.is_active ? "default" : "destructive"}>
                    {org.is_active ? "Active" : "Inactive"}
                  </Badge>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedOrg(org)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    Details
                  </Button>
                </div>
              </div>
            ))}

            {filteredOrgs.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No organizations found matching your search.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {selectedOrg && <OrganizationDetailsModal org={selectedOrg} />}
    </div>
  );
}
