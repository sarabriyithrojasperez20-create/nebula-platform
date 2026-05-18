"use client";

import { Bell, Bolt, Search } from "lucide-react";
import { motion } from "framer-motion";

export function AdminTopbar() {
  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-4 border-b border-zinc-200/80 bg-white/70 px-7 backdrop-blur-xl">
      <div className="flex max-w-md flex-1 items-center gap-3 rounded-xl border border-zinc-200/80 bg-white px-4 py-2.5 shadow-sm focus-within:border-nebula/30 focus-within:ring-2 focus-within:ring-nebula/15">
        <Search className="h-4 w-4 text-zinc-400" />
        <input
          type="search"
          placeholder="Buscar usuarios, cursos, lecciones..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-zinc-400"
        />
        <kbd className="hidden rounded border border-zinc-200 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-400 sm:inline">
          ⌘K
        </kbd>
      </div>
      <div className="flex items-center gap-2">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          type="button"
          className="hidden items-center gap-2 rounded-xl bg-nebula px-4 py-2 text-sm font-semibold text-white shadow-md shadow-nebula/25 lg:flex"
        >
          <Bolt className="h-4 w-4" />
          Acción rápida
        </motion.button>
        <button
          type="button"
          className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200/80 bg-white text-zinc-600 hover:border-nebula/20 hover:text-nebula"
        >
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-nebula ring-2 ring-white" />
        </button>
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl border border-zinc-200/80 bg-white py-1.5 pl-1.5 pr-3 hover:shadow-sm"
        >
          <img
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=nebula-admin"
            alt=""
            className="h-8 w-8 rounded-lg"
          />
          <span className="hidden text-sm font-semibold text-zinc-800 sm:block">Admin</span>
        </button>
      </div>
    </header>
  );
}
