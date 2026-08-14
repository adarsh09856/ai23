import { redirect } from "next/navigation";

import { getAuthUserApiV1UserAuthUserGet } from "@/client/sdk.gen";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { getServerAccessToken } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

/**
 * Superadmin Layout — Hard gate: admin@admin.com only.
 */
export default async function SuperadminLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const accessToken = await getServerAccessToken();

  if (!accessToken) {
    redirect("/auth/login");
  }

  try {
    const authUser = await getAuthUserApiV1UserAuthUserGet({
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!authUser.data?.is_platform_admin) {
      redirect("/overview");
    }
  } catch {
    redirect("/overview");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
