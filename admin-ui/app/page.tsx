"use client";

import { motion } from "framer-motion";
import {
  Users,
  GraduationCap,
  BookOpen,
  ClipboardCheck,
  Calendar,
  ListTodo,
  UserCheck,
} from "lucide-react";
import { AdminShell } from "@/components/admin/admin-shell";
import { KpiCard } from "@/components/admin/kpi-card";

const kpis = [
  { label: "Usuarios", value: 128, hint: "Ver detalle →", icon: Users },
  { label: "Cursos", value: 24, hint: "Catálogo activo", icon: GraduationCap },
  { label: "Lecciones", value: 186, hint: "Contenido publicado", icon: BookOpen },
  { label: "Evaluaciones", value: 412, hint: "Diagnósticos y quizzes", icon: ClipboardCheck },
];

export default function AdminDashboardPage() {
  return (
    <AdminShell>
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className="relative mb-8 overflow-hidden rounded-3xl border border-white/80 bg-white/60 p-8 shadow-card backdrop-blur-xl"
      >
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-nebula/15 blur-3xl" />
        <h1 className="relative text-3xl font-bold tracking-tight text-zinc-900">
          Bienvenido de nuevo
        </h1>
        <p className="relative mt-2 max-w-2xl text-zinc-600">
          Panel de control de tu ecosistema educativo. Métricas en tiempo real y rendimiento de
          estudiantes.
        </p>
        <div className="relative mt-5 flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            Sistema en línea
          </span>
        </div>
      </motion.section>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi, i) => (
          <motion.div
            key={kpi.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <KpiCard {...kpi} />
          </motion.div>
        ))}
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-3">
        {[
          { title: "Calendario", icon: Calendar, desc: "Eventos y evaluaciones programadas." },
          { title: "Tareas pendientes", icon: ListTodo, desc: "Evaluaciones y lecciones en curso." },
          { title: "Usuarios activos", icon: UserCheck, desc: "98 cuentas habilitadas hoy." },
        ].map((w, i) => (
          <motion.div
            key={w.title}
            whileHover={{ y: -2 }}
            className="rounded-2xl border border-zinc-200/80 bg-white/70 p-5 shadow-card backdrop-blur-xl"
          >
            <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
              <w.icon className="h-4 w-4 text-nebula" />
              {w.title}
            </h3>
            <p className="mt-2 text-sm text-zinc-500">{w.desc}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div
          className="lg:col-span-2 rounded-3xl border border-white/80 bg-white/70 p-6 shadow-card backdrop-blur-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="font-semibold text-zinc-900">Progreso de estudiantes</h3>
          <p className="text-sm text-zinc-500">Actividad semanal simulada</p>
          <div className="mt-8 flex h-48 items-end justify-between gap-2">
            {[40, 65, 55, 80, 70, 90, 60].map((h, i) => (
              <motion.div
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                transition={{ delay: 0.3 + i * 0.05, duration: 0.5 }}
                className="w-full max-w-[48px] rounded-t-lg bg-gradient-to-t from-nebula to-violet-300/60"
              />
            ))}
          </div>
        </motion.div>
        <motion.div
          className="rounded-3xl border border-white/80 bg-white/70 p-6 shadow-card backdrop-blur-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
        >
          <h3 className="font-semibold text-zinc-900">Actividad reciente</h3>
          <ul className="mt-4 space-y-4">
            {["Nuevo registro", "Curso completado", "Quiz aprobado"].map((t) => (
              <li key={t} className="flex gap-3 text-sm">
                <span className="mt-0.5 h-2 w-2 rounded-full bg-nebula" />
                <span className="text-zinc-700">{t}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      </div>
    </AdminShell>
  );
}
