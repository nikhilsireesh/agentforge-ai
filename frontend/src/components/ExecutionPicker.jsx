import { RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSelectedExecution } from "../context/ExecutionContext";
import { humanize } from "../utils/format";
import { Button, StatusBadge, inlineInputClass } from "./ui";

/** Dropdown to choose which execution an execution-scoped page shows. */
export function ExecutionPicker({ detail }) {
  const { executions, selectedId, setSelectedId, refresh } = useSelectedExecution();
  const navigate = useNavigate();

  const onChange = (event) => {
    const id = Number(event.target.value);
    setSelectedId(id);
    navigate({ search: `?execution=${id}` }, { replace: true });
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select aria-label="Select execution" value={selectedId || ""} onChange={onChange} className={`${inlineInputClass} min-w-64`}>
        {!executions.length && <option value="">No executions yet</option>}
        {executions.map((execution) => (
          <option key={execution.id} value={execution.id}>
            #{execution.id} · {execution.project_name} · {humanize(detail?.id === execution.id ? detail.status : execution.status)}
          </option>
        ))}
      </select>
      {detail && <StatusBadge status={detail.status} />}
      {detail?.llm_mode === "mock" && <StatusBadge status="mock" label="Mock LLM mode" />}
      <Button variant="ghost" size="sm" icon={RefreshCw} onClick={refresh} aria-label="Refresh executions" />
    </div>
  );
}
