import { Download, FileText, Package } from "lucide-react";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { Button, Card, EmptyState, ErrorBanner, PageHeader, Spinner, cx } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { useExecutionDetail } from "../hooks/useExecution";
import { Api } from "../services/api";

export default function Documentation() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const ex = detail.data;
  const [selected, setSelected] = useState(null);
  const docs = useApi(() => Api.artifacts(ex.project_id, { execution_id: ex.id, artifact_type: "documentation", latest_only: false }), [ex?.id, ex?.status], { enabled: Boolean(ex) });
  const documents = (docs.data || []).filter((a) => a.metadata_json?.category === "delivery_document");
  const doc = useApi(() => Api.artifact(selected), [selected], { enabled: Boolean(selected) });

  useEffect(() => {
    if (documents.length && !documents.some((d) => d.id === selected)) setSelected(documents[0].id);
  }, [documents, selected]);

  return (
    <div>
      <PageHeader title="Documentation Center" description="Delivery documents written by the Documentation agent from validated workflow data."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex ? <Spinner /> : !documents.length ? (
        <Card><EmptyState icon={FileText} title="No documentation yet" description="Documentation is generated after the final delivery approval." /></Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[260px_1fr]">
          <div className="space-y-3">
            <Card className="p-2">
              {documents.map((d) => (
                <button key={d.id} onClick={() => setSelected(d.id)}
                  className={cx("flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm cursor-pointer", selected === d.id ? "bg-violet-50 font-medium text-violet-700" : "text-slate-700 hover:bg-slate-50")}>
                  <FileText size={15} className="shrink-0" /> {d.metadata_json.title}
                </button>
              ))}
            </Card>
            <Button className="w-full" icon={Package} onClick={() => Api.downloadPackage(ex.id)}>Download delivery package</Button>
          </div>
          <Card className="min-w-0">
            <ErrorBanner error={doc.error} className="m-5" />
            {!doc.data ? <Spinner /> : (
              <>
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-3">
                  <p className="font-mono text-xs text-slate-500">{doc.data.metadata_json.relative_path}</p>
                  <Button variant="secondary" size="sm" icon={Download} onClick={() => Api.downloadArtifact(doc.data.id, doc.data.metadata_json.relative_path)}>Download .md</Button>
                </div>
                <article className="markdown px-6 py-6" data-testid="markdown-preview">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.data.content}</ReactMarkdown>
                </article>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
