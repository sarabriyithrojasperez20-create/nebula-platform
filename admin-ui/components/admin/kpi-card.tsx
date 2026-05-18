"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type KpiCardProps = {
  label: string;
  value: string | number;
  hint?: string;
  icon: LucideIcon;
  trend?: string;
  onClick?: () => void;
};

export function KpiCard({ label, value, hint, icon: Icon, trend, onClick }: KpiCardProps) {
  const Comp = onClick ? motion.button : motion.div;
  return (
    <Comp
      type={onClick ? "button" : undefined}
      onClick={onClick}
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className={cn(
        "group relative w-full overflow-hidden rounded-2xl border border-white/80 bg-white/70 p-6 text-left shadow-card backdrop-blur-xl",
        "hover:border-nebula/25 hover:shadow-nebula",
        onClick && "cursor-pointer"
      )}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-nebula/5 opacity-0 transition-opacity group-hover:opacity-100" />
      <motion.div
        className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-nebula/10 text-nebula"
        whileHover={{ scale: 1.05 }}
      >
        <Icon className="h-5 w-5" />
      </motion.div>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{label}</p>
      <p className="mt-1 text-3xl font-bold tracking-tight text-zinc-900">{value}</p>
      {(hint || trend) && (
        <p className="mt-2 text-xs font-medium text-nebula">{trend ?? hint}</p>
      )}
    </Comp>
  );
}
