import Link from "next/link";
import { ArrowRight, Database, FileText } from "lucide-react";

import { collections } from "@/lib/cms/registry";

export default function AdminDashboard() {
  const objects = collections.filter((c) => c.mode === "object");
  const lists = collections.filter((c) => c.mode === "list");

  return (
    <div>
      <h1 className="font-heading text-2xl font-bold text-charcoal">Content</h1>
      <p className="mt-1 text-sm text-muted">
        Open a section below to edit its text and pictures. Press Save on the section, then Publish in the bar at the bottom to put the changes on the live site.
      </p>

      <Section title="Site" icon={<FileText className="size-4" />} items={objects} />
      <Section title="Lists" icon={<Database className="size-4" />} items={lists} />
    </div>
  );
}

function Section({ title, icon, items }: { title: string; icon: React.ReactNode; items: typeof collections }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 flex items-center gap-2 font-heading text-xs font-bold uppercase tracking-[0.12em] text-muted">
        {icon} {title}
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((c) => (
          <Link
            key={c.id}
            href={`/admin/${c.id}`}
            className="group rounded-[6px] border border-line bg-white p-5 shadow-card transition-colors hover:border-teal"
          >
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-heading font-semibold text-charcoal">{c.label}</h3>
              <ArrowRight className="size-4 shrink-0 text-muted transition-transform group-hover:translate-x-1 group-hover:text-teal" />
            </div>
            <p className="mt-1.5 text-sm text-muted">{c.description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
