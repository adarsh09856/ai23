"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Users, Building2, Phone, Clock, Activity, TrendingUp, TrendingDown, DollarSign, Zap } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "recharts";

interface KPI {
  title: string;
  value: string | number;
  change?: string;
  trend?: "up" | "down" | "neutral";
  icon?: string;
}

interface DashboardData {
  kpis: KPI[];
  calls_timeline: Array<{ date: string; value: number }>;
  users_timeline: Array<{ date: string; value: number }>;
  top_organizations: Array<{ name: string; value: number; percentage?: number }>;
  recent_activity: Array<{
    type: string;
    timestamp: string;
    organization?: string;
    duration?: string;
  }>;
}

const iconMap = {
  users: Users,
  building: Building2,
  phone: Phone,
  clock: Clock,
  activity: Activity,
  timer: Clock,
  dollar: DollarSign,
  zap: Zap,
};

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

function KPICard({ kpi }: { kpi: KPI }) {
  const IconComponent = kpi.icon ? iconMap[kpi.icon as keyof typeof iconMap] : Activity;
  
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {kpi.title}
        </CardTitle>
        <IconComponent className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{kpi.value}</div>
        {kpi.change && (
          <div className="flex items-center text-xs mt-1">
            {kpi.trend === "up" && <TrendingUp className="mr-1 h-3 w-3 text-green-500" />}
            {kpi.trend === "down" && <TrendingDown className="mr-1 h-3 w-3 text-red-500" />}
            <span className={
              kpi.trend === "up" ? "text-green-500" : 
              kpi.trend === "down" ? "text-red-500" : 
              "text-muted-foreground"
            }>
              {kpi.change}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RecentActivityItem({ activity }: { activity: any }) {
  const getActivityDisplay = () => {
    const time = new Date(activity.timestamp).toLocaleTimeString();
    
    switch (activity.type) {
      case "call":
        return {
          text: `Call completed`,
          detail: `${activity.organization} • ${activity.duration}`,
          color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
          time
        };
      case "user_registered":
        return {
          text: "New user registered",
          detail: "",
          color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
          time
        };
      case "organization_created":
        return {
          text: "Organization created",
          detail: activity.organization,
          color: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
          time
        };
      default:
        return {
          text: activity.type.replace("_", " "),
          detail: activity.organization || "",
          color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
          time
        };
    }
  };

  const display = getActivityDisplay();
  
  return (
    <div className="flex items-start space-x-3 py-2">
      <Badge className={`text-xs ${display.color} border-0`}>
        {activity.type.replace("_", " ")}
      </Badge>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {display.text}
        </p>
        {display.detail && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {display.detail}
          </p>
        )}
        <p className="text-xs text-gray-400 dark:text-gray-500">
          {display.time}
        </p>
      </div>
    </div>
  );
}

export default function SuperAdminDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setRefreshing(!showLoading);
      
      const response = await fetch("/api/admin/analytics/dashboard", {
        credentials: "include"
      });
      
      if (response.ok) {
        const dashboardData = await response.json();
        setData(dashboardData);
        setError(null);
      } else {
        setError("Failed to load dashboard data");
      }
    } catch (err) {
      console.error("Dashboard fetch error:", err);
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    fetchDashboardData(false);
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error}</p>
        <Button onClick={() => fetchDashboardData()}>
          Retry
        </Button>
      </div>
    );
  }

  if (!data) {
    return <div className="text-center py-8">No data available</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Platform Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time analytics and platform overview
          </p>
        </div>
        <Button 
          onClick={handleRefresh} 
          disabled={refreshing}
          variant="outline"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {/* KPI Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {data.kpis.map((kpi, index) => (
          <KPICard key={index} kpi={kpi} />
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Calls Timeline */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Daily Calls</CardTitle>
            <CardDescription>
              Call volume over the last 30 days
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data.calls_timeline}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(date) => {
                    try {
                      return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    } catch {
                      return date;
                    }
                  }}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => {
                    try {
                      return new Date(date).toLocaleDateString();
                    } catch {
                      return date;
                    }
                  }}
                  formatter={(value) => [value, "Calls"]}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#2563eb" 
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest platform events (last 24 hours)
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-80 overflow-y-auto">
            <div className="space-y-1">
              {data.recent_activity.length > 0 ? (
                data.recent_activity.slice(0, 10).map((activity, index) => (
                  <RecentActivityItem key={index} activity={activity} />
                ))
              ) : (
                <p className="text-center text-muted-foreground py-4">
                  No recent activity
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* User Registrations */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Registrations</CardTitle>
            <CardDescription>New user sign-ups over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.users_timeline}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(date) => {
                    try {
                      return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    } catch {
                      return date;
                    }
                  }}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => {
                    try {
                      return new Date(date).toLocaleDateString();
                    } catch {
                      return date;
                    }
                  }}
                  formatter={(value) => [value, "New Users"]}
                />
                <Bar dataKey="value" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Top Organizations */}
        <Card>
          <CardHeader>
            <CardTitle>Top Organizations</CardTitle>
            <CardDescription>Most active organizations by call volume</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data.top_organizations.length > 0 ? (
                data.top_organizations.map((org, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{org.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {org.percentage?.toFixed(1)}% of total calls
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-sm">{org.value}</p>
                      <p className="text-xs text-muted-foreground">calls</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-center text-muted-foreground py-4">
                  No call activity in the selected period
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
