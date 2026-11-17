import { ArrowDownAZ, ArrowUpAZ, Eye, FolderKanban, Pencil, Play, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ProjectFormModal } from "../components/ProjectFormModal";
import { Button, Card, EmptyState, ErrorBanner, Modal, Spinner, StatusBadge, Table, inputClass } from "../components/ui";
import { useExecutions } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { Api, errorMessage } from "../services/api";
import { timeAgo } from "../utils/format";

const STATUSES = ["draft", "in_progress", "awaiting_approval", "completed", "failed", "archived"];

export default function Projects() {
  const navigate = useNavigate();
  const { refresh: refreshExecutions } = useExecutions();
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [status, setStatus] = useState("");
  const [domain, setDomain] = useState("");
  const [sort, setSort] = useState("updated_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const pageSize = 10;
  const { data, error, loading, reload } = useApi(
    () => Api.listProjects({ search: debounced || undefined, status: status || undefined, business_domain: domain || undefined, sort, order, page, page_size: pageSize }),
    [debounced, status, domain, sort, order, page],
  );

  const run = async (project) => {
    setBusy(project.id);
    setActionError(null);
    try {
      const execution = await Api.execute(project.id);
      await refreshExecutions();
      navigate(`/workflow?execution=${execution.id}`);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const confirmDelete = async () => {
    setActionError(null);
    try {
      await Api.deleteProject(deleting.id);
      setDeleting(null);
      reload();
      refreshExecutions();
    } catch (err) {
      setActionError(errorMessage(err));
      setDeleting(null);
    }
  };

  const columns = [
    {
      key: "name", label: "Project", render: (p) => (
        <Link to={`/projects/${p.id}`} className="group">
          <p className="font-medium text-slate-900 group-hover:text-violet-700">{p.name}</p>
          <p className="text-xs text-slate-500 line-clamp-1 max-w-md">{p.description || "No description"}</p>
        </Link>
      ),
    },
    { key: "business_domain", label: "Domain", render: (p) => p.business_domain || "—" },
    { key: "status", label: "Status", render: (p) => <StatusBadge status={p.status} /> },
    { key: "executions", label: "Runs", render: (p) => p.execution_count },
    { key: "updated", label: "Updated", render: (p) => <span className="text-slate-500">{timeAgo(p.updated_at)}</span> },
    {
      key: "actions", label: "", className: "text-right", render: (p) => (
        <div className="flex justify-end gap-1">
          <Button variant="ghost" size="sm" icon={Play} loading={busy === p.id} onClick={() => run(p)} disabled={!p.requirement_count} title={p.requirement_count ? "Run AI workflow" : "Add a requirement first"}>Run</Button>
          <Link to={`/projects/${p.id}`}><Button variant="ghost" size="sm" icon={Eye} aria-label="View" /></Link>
          <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setEditing(p)} aria-label="Edit" />
          <Button variant="ghost" size="sm" icon={Trash2} onClick={() => setDeleting(p)} aria-label="Delete" className="text-red-500" />
        </div>
      ),
    },
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="mt-1 text-sm text-slate-500">Create, search and manage client projects and their AI workflow runs.</p>
        </div>
        <Link to="/projects/new"><Button icon={Plus}>New project</Button></Link>
      </div>

      <Card className="mb-4 p-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px_180px_180px_auto]">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-2.5 text-slate-400" />
            <input className={`${inputClass} pl-9`} placeholder="Search name, description or domain…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search projects" />
          </div>
          <select className={inputClass} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Filter by status">
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
          <input className={inputClass} placeholder="Domain (exact)" value={domain} onChange={(e) => { setDomain(e.target.value); setPage(1); }} aria-label="Filter by domain" />
          <select className={inputClass} value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort by">
            <option value="updated_at">Last updated</option>
            <option value="created_at">Created</option>
            <option value="name">Name</option>
            <option value="status">Status</option>
          </select>
          <Button variant="secondary" icon={order === "asc" ? ArrowUpAZ : ArrowDownAZ} onClick={() => setOrder(order === "asc" ? "desc" : "asc")}>
            {order === "asc" ? "Asc" : "Desc"}
          </Button>
        </div>
      </Card>

      <ErrorBanner error={error || actionError} className="mb-4" />

      <Card>
        {loading && !data ? (
          <Spinner />
        ) : data?.total === 0 && !debounced && !status && !domain ? (
          <EmptyState icon={FolderKanban} title="No projects yet" description="Create your first project and let the AI agents turn a business requirement into working software."
            action={<Link to="/projects/new"><Button icon={Plus}>Create project</Button></Link>} />
        ) : (
          <>
            <Table columns={columns} rows={data?.items || []} rowKey={(p) => p.id} empty="No projects match your filters." />
            <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-sm text-slate-500">
              <span>{data?.total ?? 0} project(s)</span>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
                <span>Page {page} of {totalPages}</span>
                <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            </div>
          </>
        )}
      </Card>

      <ProjectFormModal project={editing} open={!!editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />

      <Modal open={!!deleting} title="Delete project?" onClose={() => setDeleting(null)}
        footer={<><Button variant="secondary" onClick={() => setDeleting(null)}>Cancel</Button><Button variant="danger" onClick={confirmDelete}>Delete</Button></>}>
        <p className="text-sm text-slate-600">
          <b>{deleting?.name}</b> and all its requirements, executions, logs and artifact records will be permanently deleted.
        </p>
      </Modal>
    </div>
  );
}
