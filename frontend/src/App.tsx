import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  Activity, AlertCircle, ArrowDownRight, ArrowUpRight, BellRing,
  Check, CheckCircle2, ChevronLeft, ChevronRight, Clock3,
  Command, ExternalLink, Filter, LayoutDashboard, LockKeyhole,
  LogOut, Radio, RefreshCw, Search, ShieldCheck, X,
} from "lucide-react";
import { api, ApiError } from "./api";
import { formatTimestamp, severityNames, statusNames, timeAgo } from "./format";
import type { Incident, IncidentDetail, IncidentPage, Session, Severity, Stats, Status } from "./types";

const blank: Stats = { total: 0, open: 0, acknowledged: 0, resolved: 0, critical_active: 0 };

function iconForStatus(status: Status) {
  if (status === "resolved") return <CheckCircle2 size={14} />;
  if (status === "acknowledged") return <Clock3 size={14} />;
  return <Radio size={14} />;
}

function Pill({ kind, label }: { kind: string; label: string }) {
  return <span className={`pill pill-${kind}`}>{kind === "resolved" || kind === "acknowledged" || kind === "open" ? iconForStatus(kind) : null}{label}</span>;
}

function Login({ onSuccess }: { onSuccess: (session: Session) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      onSuccess(await api.login(username, password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-accent" aria-hidden="true"><Activity size={148} strokeWidth={0.6} /></div>
      <form className="login-card" onSubmit={submit}>
        <div className="brand brand-login"><span className="brand-icon"><Activity size={22} /></span><span>Triage<span className="brand-muted">Dock</span></span></div>
        <div className="login-overline"><ShieldCheck size={15} /> OPERATOR SIGN IN</div>
        <h1>Review alerts.<br/><span>Track incidents.</span></h1>
        <p>Sign in to review incidents and their history.</p>
        <label htmlFor="username">Username</label>
        <input id="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required />
        {error && <div role="alert" className="inline-error">{error}</div>}
        <button disabled={busy} type="submit" className="button button-primary login-submit">{busy ? "Signing in…" : "Sign in to dashboard"} <ArrowUpRight size={18}/></button>
        <div className="login-foot"><LockKeyhole size={14}/> Access is restricted to authorized operators</div>
      </form>
    </div>
  );
}

function StatCard({ title, value, subtitle, tone, icon }: { title: string; value: number; subtitle: string; tone: string; icon: ReactNode }) {
  return <div className="stat-card">
    <div className="stat-head"><span>{title}</span><span className={`stat-icon ${tone}`}>{icon}</span></div>
    <div className="stat-value">{value.toLocaleString()}</div>
    <div className="stat-subtitle">{subtitle}</div>
  </div>;
}

function DetailPane({ data, onClose, onAction, busy }: {
  data: IncidentDetail; onClose: () => void;
  onAction: (action: "acknowledge" | "resolve") => Promise<void>;
  busy: boolean;
}) {
  return <div className="overlay" onMouseDown={onClose}>
    <aside className="detail-pane" role="dialog" aria-modal="true" aria-labelledby="detail-title" onMouseDown={event => event.stopPropagation()}>
      <div className="detail-top"><span className="eyebrow">INCIDENT DETAILS</span><button className="icon-button" aria-label="Close incident details" onClick={onClose}><X size={20}/></button></div>
      <h2 id="detail-title">{data.title}</h2>
      <div className="pills"><Pill kind={data.severity} label={severityNames[data.severity]} /><Pill kind={data.status} label={statusNames[data.status]} /></div>
      <div className="detail-section">
        <div className="section-label">DESCRIPTION</div>
        <p>{data.description || "No description provided."}</p>
      </div>
      <div className="detail-grid">
        <div><div className="section-label">SOURCE</div><strong>{data.source}</strong></div>
        <div><div className="section-label">OCCURRENCES</div><strong>{data.occurrences}</strong></div>
        <div><div className="section-label">EXTERNAL KEY</div><strong className="mono wrap-word">{data.external_key}</strong></div>
        <div><div className="section-label">LAST OBSERVED</div><strong>{formatTimestamp(data.last_seen_at)}</strong></div>
      </div>
      {data.status !== "resolved" && <div className="detail-actions">
        {data.status === "open" && <button className="button button-secondary" disabled={busy} onClick={() => void onAction("acknowledge")}><Check size={16}/> Acknowledge</button>}
        <button className="button button-primary" disabled={busy} onClick={() => void onAction("resolve")}><CheckCircle2 size={16}/> Resolve incident</button>
      </div>}
      <div className="detail-section">
        <div className="section-label">ACTIVITY HISTORY</div>
        <div className="timeline">
          {data.events.map(event => <div className="timeline-entry" key={event.id}>
            <div className="timeline-dot"/>
            <div><strong>{event.kind[0].toUpperCase() + event.kind.slice(1)}</strong><div className="muted small">{formatTimestamp(event.created_at)}{event.actor ? ` · ${event.actor}` : ""}</div></div>
          </div>)}
        </div>
      </div>
      <div className="detail-section">
        <div className="section-label">NOTIFICATION DELIVERY</div>
        {data.deliveries.length === 0 ? <p className="muted small">No delivery attempts recorded for this incident. Outbound notifications require an HTTPS webhook configured on the server.</p> :
          data.deliveries.map(delivery => <div className="delivery-row" key={delivery.id}><span>{delivery.event_kind}</span><Pill kind={delivery.status} label={delivery.status} /><span className="muted small">{delivery.attempts} attempts</span></div>)}
      </div>
    </aside>
  </div>;
}

function Dashboard({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const [stats, setStats] = useState<Stats>(blank);
  const [pageData, setPageData] = useState<IncidentPage | null>(null);
  const [status, setStatus] = useState<Status | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastLoaded, setLastLoaded] = useState<Date | null>(null);
  const [reload, setReload] = useState(0);

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const [counts, result] = await Promise.all([
        api.stats(),
        api.list({ status: status || undefined, severity: severity || undefined, q: query, page }),
      ]);
      setStats(counts);
      setPageData(result);
      setLastLoaded(new Date());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load incidents.");
    } finally {
      setLoading(false);
    }
  }, [status, severity, query, page]);

  useEffect(() => { void load(); }, [load, reload]);

  useEffect(() => {
    const refresh = window.setInterval(() => setReload(value => value + 1), 30000);
    return () => window.clearInterval(refresh);
  }, []);

  useEffect(() => {
    if (!detail) return;
    const onEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setDetail(null); };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [detail]);

  async function openIncident(incident: Incident) {
    setError("");
    try { setDetail(await api.detail(incident.id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to open incident."); }
  }

  async function action(name: "acknowledge" | "resolve") {
    if (!detail) return;
    setBusy(true);
    setError("");
    try {
      setDetail(await api.action(detail.id, name));
      setReload(value => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    try { await api.logout(); onLogout(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not sign out."); }
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault(); setPage(1); setQuery(search.trim());
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon"><Activity size={21}/></span><span>Triage<span className="brand-muted">Dock</span></span></div>
      <div className="nav-caption">WORKSPACE</div>
      <div className="nav-item selected"><LayoutDashboard size={18}/> Overview <span className="nav-indicator"/></div>
      <div className="sidebar-bottom">
        <div className="system-status"><RefreshCw size={14}/> Checks for updates every 30 seconds</div>
        <div className="account"><div className="avatar">{(session.username || "O").slice(0, 1).toUpperCase()}</div><div className="account-text"><strong>{session.username}</strong><span>Operator</span></div><button className="icon-button" aria-label="Sign out" title="Sign out" onClick={() => void logout()}><LogOut size={17}/></button></div>
      </div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={14}/> <strong>Overview</strong></div><div className="top-actions"><span className="live"><RefreshCw size={13}/> 30 SECOND REFRESH</span><span className="top-divider"/><span className="user-label">{session.username}</span></div></header>
      <div className="content">
        <div className="page-intro"><div><div className="eyebrow"><span className="eyebrow-line"/> INCIDENT REVIEW</div><h1>Incident dashboard<span className="heading-period">.</span></h1><p>Review incoming alerts, update their status, and inspect activity history.</p></div><button className="button button-secondary refresh" onClick={() => setReload(value => value + 1)} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""}/> Refresh data</button></div>
        {error && <div role="alert" className="error-banner"><AlertCircle size={18}/><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError("")}><X size={15}/></button></div>}
        <div className="stat-grid">
          <StatCard title="Total incidents" value={stats.total} subtitle="All recorded incidents" tone="blue" icon={<Activity size={20}/>} />
          <StatCard title="Open incidents" value={stats.open} subtitle="Awaiting attention" tone="orange" icon={<ArrowUpRight size={20}/>} />
          <StatCard title="Critical & active" value={stats.critical_active} subtitle="Requires immediate review" tone="red" icon={<BellRing size={20}/>} />
          <StatCard title="Resolved" value={stats.resolved} subtitle="Marked resolved" tone="green" icon={<CheckCircle2 size={20}/>} />
        </div>
        <section className="table-card">
          <div className="table-titlebar"><div><h2>Incident feed</h2><p>Alerts received by TriageDock. List refreshes every 30 seconds.</p></div><span className="count-badge">{pageData?.count ?? 0} incidents</span></div>
          <div className="filters">
            <form className="search-field" onSubmit={submitSearch}><Search size={17}/><input aria-label="Search incidents" placeholder="Search incidents, sources, keys…" value={search} onChange={event => setSearch(event.target.value)}/><button type="submit">Search</button></form>
            <div className="select-wrap"><Filter size={15}/><select aria-label="Filter by status" value={status} onChange={event => { setStatus(event.target.value as Status | ""); setPage(1); }}><option value="">All statuses</option><option value="open">Open</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select></div>
            <div className="select-wrap"><select aria-label="Filter by severity" value={severity} onChange={event => { setSeverity(event.target.value as Severity | ""); setPage(1); }}><option value="">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>
          </div>
          <div className="table-scroll">
            <table><thead><tr><th>INCIDENT</th><th>SEVERITY</th><th>STATUS</th><th>OCCURRENCES</th><th>LAST SEEN</th><th><span className="sr-only">Open details</span></th></tr></thead>
              <tbody>{pageData?.results.map(incident => <tr key={incident.id} onClick={() => void openIncident(incident)}>
                <td><div className="incident-cell"><span className={`incident-mark mark-${incident.severity}`}>{incident.severity === "critical" ? <AlertCircle size={18}/> : <Activity size={18}/>}</span><div><div className="incident-title">{incident.title}</div><div className="incident-source">{incident.source} <span className="separator">·</span> {incident.external_key}</div></div></div></td>
                <td><Pill kind={incident.severity} label={severityNames[incident.severity]}/></td>
                <td><Pill kind={incident.status} label={statusNames[incident.status]}/></td>
                <td><span className="occurrence">{incident.occurrences}</span></td>
                <td className="muted nowrap">{timeAgo(incident.last_seen_at)}</td>
                <td><button className="table-open" aria-label={`Open ${incident.title}`} onClick={event => { event.stopPropagation(); void openIncident(incident); }}><ExternalLink size={16}/></button></td>
              </tr>)}</tbody>
            </table>
            {!loading && pageData?.results.length === 0 && <div className="empty"><ShieldCheck size={34}/><strong>No incidents found</strong><span>{stats.total === 0 ? "Send your first alert to populate the feed." : "Try a different filter or search."}</span></div>}
            {loading && !pageData && <div className="empty"><RefreshCw className="spin" size={28}/> Loading incidents…</div>}
          </div>
          <div className="table-footer"><div>{pageData ? `Showing ${pageData.results.length} incidents on page ${page} of ${pageData.count} total` : "No data loaded"} <span className="footer-dot">·</span> {lastLoaded ? `Updated ${lastLoaded.toLocaleTimeString()}` : "Connecting"}</div><div className="paging"><button aria-label="Previous page" disabled={!pageData?.previous || loading} onClick={() => setPage(value => Math.max(1, value - 1))}><ChevronLeft size={17}/></button><span>{page}</span><button aria-label="Next page" disabled={!pageData?.next || loading} onClick={() => setPage(value => value + 1)}><ChevronRight size={17}/></button></div></div>
        </section>
        <footer className="page-foot"><span><Command size={15}/> TriageDock <span className="footer-dot">·</span> Incident intake and response</span><span><ArrowDownRight size={14}/> Data refreshes every 30 seconds</span></footer>
      </div>
    </main>
    {detail && <DetailPane data={detail} onClose={() => setDetail(null)} onAction={action} busy={busy}/>}
  </div>;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.session().then(setSession).catch((reason: unknown) =>
      setError(reason instanceof ApiError ? reason.message : "Unable to connect to the server."));
  }, []);
  if (!session) return <div className="startup"><div className="brand"><span className="brand-icon"><Activity size={20}/></span>TriageDock</div><p>{error || "Connecting to incident services…"}</p>{error && <button className="button button-secondary" onClick={() => window.location.reload()}>Retry connection</button>}</div>;
  return session.authenticated
    ? <Dashboard session={session} onLogout={() => setSession({authenticated: false, username: null})}/>
    : <Login onSuccess={setSession}/>;
}
