import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

export function Sidebar({ children, className }: { children: ReactNode; className?: string }): ReactNode {
  return (
    <aside
      className={cn(
        "flex w-64 shrink-0 flex-col border-r border-zinc-200 bg-zinc-50 text-zinc-950 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-50",
        className,
      )}
    >
      {children}
    </aside>
  );
}

export function SidebarInset({ children }: { children: ReactNode }): ReactNode {
  return <div className="flex min-w-0 flex-1 flex-col">{children}</div>;
}

export function SidebarHeader({ children }: { children: ReactNode }): ReactNode {
  return <div className="px-4 py-4 text-sm font-semibold tracking-tight">{children}</div>;
}

export function SidebarContent({ children }: { children: ReactNode }): ReactNode {
  return <div className="flex-1 px-2">{children}</div>;
}

export function SidebarFooter({ children }: { children: ReactNode }): ReactNode {
  return <div className="mt-auto border-t border-zinc-200 p-3 dark:border-zinc-800">{children}</div>;
}

export function SidebarMenu({ children }: { children: ReactNode }): ReactNode {
  return (
    <ul className="flex flex-col gap-1">
      {children}
    </ul>
  );
}

export function SidebarMenuItem({ children }: { children: ReactNode }): ReactNode {
  return <li>{children}</li>;
}
