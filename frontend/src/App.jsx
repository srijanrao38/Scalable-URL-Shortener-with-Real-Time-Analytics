import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#22d3ee", "#a78bfa", "#f472b6", "#fbbf24", "#34d399"];

async function apiRequest(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || "The request failed.");
    error.status = response.status;
    error.retryAfter = response.headers.get("Retry-After");
    throw error;
  }
  return body;
}

function PageShell({ children, onHome }) {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 py-8 sm:px-8">
      <header className="mb-10 flex items-center justify-between">
        <button onClick={onHome} className="text-left">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-300">Link Lab</p>
          <h1 className="text-2xl font-bold text-white">Short links, clear signals.</h1>
        </button>
        <button onClick={() => { window.location.hash = "dashboard"; }} className="text-sm text-slate-300 hover:text-white">
          Analytics dashboard →
        </button>
      </header>
      {children}
    </main>
  );
}

function CreateLink() {
  const [longUrl, setLongUrl] = useState("");
  const [created, setCreated] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setCreated(null);
    setLoading(true);
    try {
      setCreated(await apiRequest("/links", { method: "POST", body: JSON.stringify({ long_url: longUrl }) }));
      setLongUrl("");
    } catch (requestError) {
      setError(requestError.status === 429
        ? `Too many requests. Try again in ${requestError.retryAfter || "a moment"} seconds.`
        : requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function copyLink() {
    await navigator.clipboard.writeText(created.short_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
      <div>
        <p className="mb-4 inline-flex rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-200">FastAPI · Redis · Postgres</p>
        <h2 className="max-w-xl text-5xl font-bold leading-tight text-white sm:text-6xl">Turn a long URL into a useful signal.</h2>
        <p className="mt-6 max-w-xl text-lg leading-8 text-slate-400">Create a short link, share it anywhere, and understand how people use it without storing raw IP addresses.</p>
      </div>
      <form onSubmit={submit} className="card">
        <label htmlFor="long-url" className="mb-2 block text-sm font-medium text-slate-200">Paste a destination URL</label>
        <input id="long-url" type="url" required value={longUrl} onChange={(event) => setLongUrl(event.target.value)} placeholder="https://example.com/a-long-path" className="mb-4 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-cyan-400 focus:ring-2" />
        <button className="button-primary w-full" disabled={loading}>{loading ? "Creating…" : "Create short link"}</button>
        {error && <p role="alert" className="mt-4 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
        {created && (
          <div className="mt-5 rounded-lg border border-emerald-400/30 bg-emerald-400/10 p-4">
            <p className="text-xs uppercase tracking-wider text-emerald-200">Your short link</p>
            <div className="mt-2 flex items-center gap-2">
              <a className="min-w-0 flex-1 truncate font-semibold text-emerald-100" href={created.short_url}>{created.short_url}</a>
              <button type="button" onClick={copyLink} className="rounded-md border border-emerald-300/40 px-3 py-1 text-sm text-emerald-100 hover:bg-emerald-300/10">{copied ? "Copied" : "Copy"}</button>
            </div>
          </div>
        )}
      </form>
    </section>
  );
}

function Dashboard() {
  const [links, setLinks] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { apiRequest("/links").then(setLinks).catch((e) => setError(e.message)); }, []);
  return (
    <section>
      <div className="mb-6 flex items-end justify-between"><div><p className="text-sm text-cyan-300">Overview</p><h2 className="text-4xl font-bold text-white">Your links</h2></div><button className="button-primary" onClick={() => { window.location.hash = ""; }}>New link</button></div>
      {links === null && !error && <p className="text-slate-400">Loading links…</p>}
      {error && <p role="alert" className="text-rose-300">{error}</p>}
      {links?.length === 0 && <div className="card text-slate-400">No links yet. Create your first one.</div>}
      <div className="grid gap-4">{links?.map((link) => <button key={link.code} onClick={() => { window.location.hash = `link/${link.code}`; }} className="card flex items-center justify-between text-left transition hover:border-cyan-400/50"><div className="min-w-0"><p className="font-semibold text-cyan-200">{link.short_url}</p><p className="truncate text-sm text-slate-400">{link.long_url}</p></div><div className="ml-4 shrink-0 text-right"><p className="text-2xl font-bold text-white">{link.click_count}</p><p className="text-xs uppercase tracking-wider text-slate-500">clicks</p></div></button>)}</div>
    </section>
  );
}

function ChartCard({ title, children, empty }) {
  return <div className="card"><h3 className="mb-4 font-semibold text-white">{title}</h3>{empty ? <p className="py-12 text-center text-sm text-slate-500">No data yet.</p> : children}</div>;
}

function Detail({ code }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { apiRequest(`/links/${code}/stats`).then(setStats).catch((e) => setError(e.message)); }, [code]);
  const daily = useMemo(() => stats?.clicks_per_day || [], [stats]);
  if (error) return <p role="alert" className="text-rose-300">{error}</p>;
  if (!stats) return <p className="text-slate-400">Loading analytics…</p>;
  return <section><button onClick={() => { window.location.hash = "dashboard"; }} className="mb-6 text-sm text-cyan-300">← Back to dashboard</button><div className="mb-7 flex items-end justify-between"><div><p className="text-sm text-cyan-300">Analytics</p><h2 className="text-4xl font-bold text-white">/{stats.code}</h2></div><p className="text-right"><span className="block text-4xl font-bold text-white">{stats.total_clicks}</span><span className="text-xs uppercase tracking-wider text-slate-500">total clicks</span></p></div><div className="grid gap-5 lg:grid-cols-2"><ChartCard title="Clicks per day" empty={!daily.length}><div className="h-72"><ResponsiveContainer width="100%" height="100%"><LineChart data={daily}><CartesianGrid stroke="#1e293b" /><XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} stroke="#64748b" /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} /><Line type="monotone" dataKey="clicks" stroke="#22d3ee" strokeWidth={3} /></LineChart></ResponsiveContainer></div></ChartCard><ChartCard title="Devices" empty={!stats.device_breakdown.length}><div className="h-72"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={stats.device_breakdown} dataKey="count" nameKey="name" outerRadius={90} label>{stats.device_breakdown.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer></div></ChartCard><ChartCard title="Browsers" empty={!stats.browser_breakdown.length}><div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={stats.browser_breakdown}><CartesianGrid stroke="#1e293b" /><XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} stroke="#64748b" /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} /><Bar dataKey="count" fill="#a78bfa" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div></ChartCard></div></section>;
}

export default function App() {
  const [hash, setHash] = useState(window.location.hash.slice(1));
  useEffect(() => { const onHash = () => setHash(window.location.hash.slice(1)); window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  const detailCode = hash.startsWith("link/") ? hash.slice(5) : null;
  return <PageShell onHome={() => { window.location.hash = ""; }}>{detailCode ? <Detail code={detailCode} /> : hash === "dashboard" ? <Dashboard /> : <CreateLink />}</PageShell>;
}
