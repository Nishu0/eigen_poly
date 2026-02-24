import { Button } from "@eigenpoly/ui";

const cards = [
  {
    title: "Register",
    detail: "Create production agent accounts and persist credentials safely"
  },
  {
    title: "Balance",
    detail: "Fetch canonical balances across Polygon Safe + Solana vaults"
  },
  {
    title: "Trade",
    detail: "Submit market-aware trades with risk guardrails and receipts"
  }
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-10 px-6 py-16">
      <section className="space-y-4">
        <p className="text-sm uppercase tracking-[0.35em] text-orange-300">Agents & Trading</p>
        <h1 className="text-5xl font-semibold leading-tight">Verifiable Intent Engines</h1>
        <p className="max-w-3xl text-lg text-slate-300">
          Natural language intents are compiled into explicit action plans with per-step receipts,
          strict allowlists, and dynamic risk controls.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {cards.map((card) => (
          <article key={card.title} className="rounded-xl border border-slate-700 bg-slate-900/60 p-5">
            <h2 className="text-xl font-medium">{card.title}</h2>
            <p className="mt-2 text-sm text-slate-300">{card.detail}</p>
          </article>
        ))}
      </section>

      <section className="flex items-center gap-3">
        <Button>Launch Agent Console</Button>
        <Button variant="outline">View API Routes</Button>
      </section>
    </main>
  );
}
