"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  BarChart3,
  Users,
  BookOpen,
  GraduationCap,
  ClipboardCheck,
  Sparkles,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";

const mainNav = [
  { href: "/", label: "Gestión", icon: LayoutDashboard },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

const contentNav = [
  { href: "/users", label: "Usuarios", icon: Users },
  { href: "/courses", label: "Cursos", icon: GraduationCap },
  { href: "/lessons", label: "Lecciones", icon: BookOpen },
  { href: "/evaluations", label: "Evaluaciones", icon: ClipboardCheck },
];

function NavItem({
  href,
  label,
  icon: Icon,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  const pathname = usePathname();
  const active = pathname === href;
  return (
    <Link href={href} className="block">
      <motion.span
        className={cn(
          "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
          active
            ? "bg-nebula/12 text-nebula shadow-sm"
            : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
        )}
        whileTap={{ scale: 0.98 }}
      >
        <Icon className={cn("h-[18px] w-[18px]", active && "text-nebula")} />
        {label}
      </motion.span>
    </Link>
  );
}

export function AdminSidebar() {
  return (
    <aside className="fixed left-0 top-0 z-50 flex h-screen w-[260px] flex-col border-r border-zinc-200/80 bg-white/70 p-4 backdrop-blur-xl">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 flex items-center gap-3 px-2 py-2"
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-nebula to-violet-400 text-white shadow-lg shadow-nebula/30">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-zinc-900">Nébula</p>
          <p className="text-[10px] font-medium text-zinc-500">Admin Console</p>
        </div>
      </motion.div>

      <nav className="flex-1 space-y-6 overflow-y-auto">
        <div>
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-400">
            Principal
          </p>
          <div className="space-y-1">
            {mainNav.map((item) => (
              <NavItem key={item.href} {...item} />
            ))}
          </div>
        </div>
        <div>
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-zinc-400">
            Contenido
          </p>
          <div className="space-y-1">
            {contentNav.map((item) => (
              <NavItem key={item.href} {...item} />
            ))}
          </div>
        </div>
      </nav>

      <div className="mt-auto space-y-3 border-t border-zinc-200/80 pt-4">
        <motion.div
          className="rounded-2xl border border-nebula/15 bg-gradient-to-br from-nebula/10 to-violet-50 p-4"
          whileHover={{ scale: 1.01 }}
        >
          <p className="text-xs font-semibold text-nebula">Plan Pro</p>
          <p className="mt-1 text-[11px] leading-relaxed text-zinc-600">
            Reportes avanzados y exportación ilimitada.
          </p>
          <button
            type="button"
            className="mt-3 w-full rounded-lg bg-nebula py-2 text-xs font-semibold text-white shadow-md shadow-nebula/25"
          >
            Explorar planes
          </button>
        </motion.div>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50"
        >
          <LogOut className="h-[18px] w-[18px]" />
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
