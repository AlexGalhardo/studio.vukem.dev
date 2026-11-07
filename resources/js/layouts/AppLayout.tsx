import { Link, usePage } from "@inertiajs/react";
import { Clapperboard, LayoutDashboard, LogOut } from "lucide-react";
import type { ReactNode } from "react";

import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarInset, SidebarMenu, SidebarMenuItem } from "../components/ui/sidebar";
import type { SharedProps } from "../types";

const item = "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-zinc-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:hover:bg-zinc-800";

export default function AppLayout({ children }: { children: ReactNode }) {
  const page = usePage<SharedProps>();
  const { auth } = page.props;
  const message = page.flash?.success ?? page.flash?.status;
  const notice = typeof message === "string" ? (
    <p role="status" className="mb-4 rounded-md bg-indigo-50 px-4 py-3 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-100">
      {message}
    </p>
  ) : null;

  if (!auth?.user) {
    return (
      <main className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center p-6">
        {notice}
        {children}
      </main>
    );
  }

  return (
    <div className="flex min-h-svh">
      <Sidebar>
        <SidebarHeader>
          <Link href="/" className="rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">
            {page.props.appName}
          </Link>
        </SidebarHeader>
        <SidebarContent>
          <nav aria-label="Dashboard">
            <SidebarMenu>
              <SidebarMenuItem>
                <Link href="/" className={item}>
                  <LayoutDashboard aria-hidden="true" className="size-4" />
                  Dashboard
                </Link>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <Link href="/jobs" className={item}>
                  <Clapperboard aria-hidden="true" className="size-4" />
                  Videos
                </Link>
              </SidebarMenuItem>
            </SidebarMenu>
          </nav>
        </SidebarContent>
        <SidebarFooter>
          <p className="truncate px-3 text-sm">{auth.user.name}</p>
          <Link href="/logout" method="post" as="button" className={item}>
            <LogOut aria-hidden="true" className="size-4" />
            Log out
          </Link>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <main className="flex-1 p-6">
          {notice}
          {children}
        </main>
      </SidebarInset>
    </div>
  );
}
