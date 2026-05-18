"use client";

import { AdminSidebar } from "./sidebar";
import { AdminTopbar } from "./topbar";

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f6f5f9] font-sans text-zinc-900">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_50%_at_0%_-10%,rgba(109,74,255,0.14),transparent_50%),radial-gradient(ellipse_60%_40%_at_100%_0%,rgba(139,108,255,0.08),transparent_45%)]" />
      <AdminSidebar />
      <div className="relative ml-[260px]">
        <AdminTopbar />
        <main className="p-7">{children}</main>
      </div>
    </div>
  );
}
