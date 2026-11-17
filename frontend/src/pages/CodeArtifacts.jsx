import { ChevronRight, Code2, Download, FileCode2, Folder, Package } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { CodeBlock } from "../components/CodeBlock";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { Button, Card, EmptyState, ErrorBanner, KeyValue, Notice, PageHeader, Spinner, StatusBadge, cx, inlineInputClass } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { useExecutionDetail } from "../hooks/useExecution";
import { Api } from "../services/api";

function buildTree(files) {
  const root = { folders: {}, files: [] };
  for (const file of files) {
    const parts = file.metadata_json.relative_path.split("/");
    let node = root;
    for (const part of parts.slice(0, -1)) node = node.folders[part] ||= { folders: {}, files: [] };
    node.files.push(file);
  }
  return root;
}

function Tree({ node, depth = 0, selected, onSelect }) {
  return (
    <>
      {Object.entries(node.folders).sort().map(([name, child]) => (
        <div key={name}>
          <div className="flex items-center gap-1.5 py-1 text-sm text-slate-600" style={{ paddingLeft: depth * 14 + 8 }}>
            <ChevronRight size={13} className="rotate-90 text-slate-400" /><Folder size={14} className="text-violet-400" /> {name}
          </div>
          <Tree node={child} depth={depth + 1} selected={selected} onSelect={onSelect} />
        </div>
      ))}
      {node.files.sort((a, b) => a.file_path.localeCompare(b.file_path)).map((file) => (
        <button key={file.id} onClick={() => onSelect(file.id)}
          className={cx("flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-sm cursor-pointer", selected === file.id ? "bg-violet-50 font-medium text-violet-700" : "text-slate-700 hover:bg-slate-50")}
          style={{ paddingLeft: depth * 14 + 26 }}>
          <FileCode2 size={14} className="shrink-0 text-slate-400" />
          <span className="truncate">{file.metadata_json.relative_path.split("/").pop()}</span>
          {file.metadata_json.proposed_action === "update" && <span className="ml-auto text-[10px] text-amber-600">M</span>}
        </button>
      ))}
    </>
  );
}

export default function CodeArtifacts() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const ex = detail.data;
  const [version, setVersion] = useState("latest");
  const [selected, setSelected] = useState(null);

  const all = useApi(() => Api.artifacts(ex.project_id, { execution_id: ex.id, latest_only: false }), [ex?.id, ex?.status, ex?.current_agent], { enabled: Boolean(ex) });
  const code = useMemo(() => (all.data || []).filter((a) => a.metadata_json?.category === "code"), [all.data]);
  const versions = [...new Set(code.map((a) => a.metadata_json.code_version))].sort((a, b) => a - b);
  const activeVersion = version === "latest" ? versions[versions.length - 1] : Number(version);
  const files = code.filter((a) => a.metadata_json.code_version === activeVersion);
  const file = useApi(() => Api.artifact(selected), [selected], { enabled: Boolean(selected) });

  useEffect(() => {
    if (files.length && !files.some((f) => f.id === selected)) {
      setSelected((files.find((f) => f.metadata_json.relative_path === "app/main.py") || files[0]).id);
    }
  }, [files, selected]);

  const meta = file.data?.metadata_json || {};
  return (
    <div>
      <PageHeader title="Code Artifacts" description="Files proposed by the Developer agent. They are stored in an isolated folder and never executed on the host."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex ? <Spinner /> : (
        <div className="space-y-5">
          <ErrorBanner error={detail.error || all.error} />
          {ex.pending_approval?.checkpoint === "code" && <ApprovalPanel approval={ex.pending_approval} executionId={ex.id} showLink={false} onDecided={detail.reload} />}
          {!code.length ? (
            <Card><EmptyState icon={Code2} title="No code generated yet" description="Approve the architecture checkpoint and the Developer agent will generate code." /></Card>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <select className={inlineInputClass} value={version} onChange={(e) => setVersion(e.target.value)} aria-label="Code version">
                  <option value="latest">Latest version (v{versions[versions.length - 1]})</option>
                  {versions.map((v) => <option key={v} value={v}>Version {v}{v > 1 ? " (after correction/revision)" : " (initial)"}</option>)}
                </select>
                <span className="text-sm text-slate-500">{files.length} files</span>
                <div className="ml-auto flex gap-2">
                  {ex.status === "completed" && <Button variant="secondary" icon={Package} onClick={() => Api.downloadPackage(ex.id)}>Download delivery package</Button>}
                </div>
              </div>
              {files.some((f) => f.metadata_json.description?.includes("MOCK DEMO")) && (
                <Notice tone="warning">This version contains a defect that mock mode injected on purpose, so you can watch the review agent catch it and the correction loop fix it.</Notice>
              )}
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-[280px_1fr]">
                <Card className="p-2 lg:max-h-[640px] lg:overflow-y-auto">
                  <Tree node={buildTree(files)} selected={selected} onSelect={setSelected} />
                </Card>
                <Card className="min-w-0 overflow-hidden">
                  {!file.data ? <Spinner /> : (
                    <>
                      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
                        <div className="min-w-0">
                          <p className="font-mono text-sm font-semibold text-slate-900">{meta.relative_path}</p>
                          <p className="mt-0.5 text-sm text-slate-500">{meta.description}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={file.data.approval_status} />
                          <Button variant="secondary" size="sm" icon={Download} onClick={() => Api.downloadArtifact(file.data.id, meta.relative_path.split("/").pop())}>Download</Button>
                        </div>
                      </div>
                      <div className="border-b border-slate-100 bg-slate-50/60 px-5 py-3">
                        <KeyValue items={[
                          ["Proposed change", meta.proposed_action],
                          ["Version", `v${meta.code_version}`],
                          ["Size", `${meta.size_bytes} bytes`],
                          ["Dependencies", meta.dependencies?.join(", ") || "—"],
                          ["SHA-256", <span key="sha" className="font-mono text-xs">{meta.sha256?.slice(0, 16)}…</span>],
                          ["Generated by", meta.is_mock ? "Mock template generator" : "LLM Developer agent"],
                        ]} />
                      </div>
                      <div className="max-h-[520px] overflow-auto bg-white">
                        {file.data.content ? <CodeBlock code={file.data.content} path={meta.relative_path} /> : <p className="p-5 text-sm text-slate-400">(empty file)</p>}
                      </div>
                    </>
                  )}
                </Card>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
