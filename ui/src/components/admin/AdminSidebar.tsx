"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { 
  LayoutDashboard, 
  Users, 
  Building2, 
  Settings, 
  BarChart3,
  Key,
  Phone
} from "lucide-react";

const navigation = [
  {
    name: "Dashboard",
    href: "/superadmin",
    icon: LayoutDashboard,
    current: false,
  },
  {
    name: "Users",
    href: "/superadmin/users",
    icon: Users,
    current: false,
  },
  {
    name: "Organizations", 
    href: "/superadmin/organizations",
    icon: Building2,
    current: false,
  },
  {
    name: "Analytics",
    href: "/superadmin/analytics",
    icon: BarChart3,
    current: false,
  },
  {
    name: "Calls",
    href: "/superadmin/calls",
    icon: Phone,
    current: false,
  },
  {
    name: "Provider Keys",
    href: "/superadmin/settings/providers", 
    icon: Key,
    current: false,
  },
  {
    name: "Settings",
    href: "/superadmin/settings",
    icon: Settings,
    current: false,
  },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col bg-gray-50 dark:bg-gray-900">
      <div className="flex h-16 flex-shrink-0 items-center border-b border-gray-200 dark:border-gray-700 px-4">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Admin Panel
        </h1>
      </div>
      <div className="flex flex-1 flex-col overflow-y-auto pt-5 pb-4">
        <nav className="flex-1 space-y-1 px-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== "/superadmin" && pathname.startsWith(item.href));
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800",
                  "group flex items-center rounded-md px-2 py-2 text-sm font-medium transition-colors"
                )}
              >
                <item.icon
                  className={cn(
                    isActive
                      ? "text-primary-foreground"
                      : "text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300",
                    "mr-3 h-5 w-5 flex-shrink-0"
                  )}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
