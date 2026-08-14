import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

import { getAuthUserApiV1UserAuthUserGet } from "@/client/sdk.gen";
import { getWorkflowCountApiV1WorkflowCountGet } from "@/client/sdk.gen";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getRandomId() {
  return Math.floor(Math.random() * 10_000);
}

export function getNextNodeId(existingNodes: { id: string }[]): string {
  const numericIds = existingNodes
    .map(node => parseInt(node.id, 10))
    .filter(id => !isNaN(id));

  const maxId = numericIds.length > 0 ? Math.max(...numericIds) : 0;
  return String(maxId + 1);
}

export function debounce<T extends (...args: unknown[]) => unknown>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function (...args: Parameters<T>) {
    if (timeout) {
      clearTimeout(timeout);
    }

    timeout = setTimeout(() => {
      func(...args);
    }, wait);
  };
}

export async function getRedirectUrl(token: string, permissions: { id: string }[] = []) {
  console.log('[getRedirectUrl] Called with:', {
    hasToken: !!token,
    tokenLength: token?.length,
    permissionsCount: permissions.length,
    permissions: permissions.map(p => p.id)
  });
  try {
    console.log('[getRedirectUrl] Calling getAuthUserApiV1UserAuthUserGet...');
    const authUser = await getAuthUserApiV1UserAuthUserGet({
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    console.log('[getRedirectUrl] Auth user response:', {
      hasData: !!authUser.data,
      isSuperuser: authUser.data?.is_superuser,
      isPlatformAdmin: authUser.data?.is_platform_admin,
      email: authUser.data?.email,
      userId: authUser.data?.id
    });
    
    // Only redirect to /superadmin if user is the reserved platform admin (admin@admin.com)
    if (authUser.data?.is_platform_admin) {
      console.log('[getRedirectUrl] User is reserved platform admin (admin@admin.com), redirecting to /superadmin');
      return "/superadmin";
    }

    const hasAdminPermission = permissions.some(p => p.id === 'admin');
    console.log('[getRedirectUrl] Admin permission check:', { hasAdminPermission });

  // If the user doesn't have admin permissions, redirect them to
  // usage page
  if (!hasAdminPermission) {
    console.log('[getRedirectUrl] No admin permission, redirecting to /usage');
    return "/usage";
  }

  // Check if user has any workflows
  try {
    console.log('[getRedirectUrl] Checking for existing workflows...');
    const countResponse = await getWorkflowCountApiV1WorkflowCountGet({
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    console.log('[getRedirectUrl] Found workflows:', {
      total: countResponse.data?.total,
      active: countResponse.data?.active
    });

    if (countResponse.data && countResponse.data.active > 0) {
      console.log('[getRedirectUrl] User has workflows, redirecting to /workflow');
      return "/workflow";
    } else {
      console.log('[getRedirectUrl] No workflows found, redirecting to /workflow/create');
      return "/workflow/create";
    }
  } catch (error) {
    console.error('[getRedirectUrl] Error checking workflows:', error);
    // If we can't check workflows, default to /workflow/create
    console.log('[getRedirectUrl] Defaulting to /workflow/create due to error');
    return "/workflow/create";
  }
  } catch (error) {
    console.error("[getRedirectUrl] Failed to fetch auth user:", error);
    // Re-throw the error so the caller can handle it
    throw error;
  }
}

