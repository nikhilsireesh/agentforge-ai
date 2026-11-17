import { CheckCircle2, RotateCcw, ShieldAlert, XCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Api, errorMessage } from "../services/api";
import { CHECKPOINT_LABELS, CHECKPOINT_PAGES, humanize, timeAgo } from "../utils/format";
import { Button, ErrorBanner, Modal, inputClass } from "./ui";

function SummaryValue({ value }) {
  if (Array.isArray(value)) return <span>{value.length ? value.join(", ") : "—"}</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  return <span>{value ?? "—"}</span>;
}

/**
 * Human-in-the-loop decision form for a pending checkpoint.
 * Approve resumes the workflow; "Request revision" sends feedback back to the agent;
 * "Reject" stops the workflow.
 */
export function ApprovalPanel({ approval, executionId, onDecided, showLink = true, compact = false }) {
  const { canApprove } = useAuth();
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [confirmReject, setConfirmReject] = useState(false);

  if (!approval) return null;
  const { question, ...summary } = approval.summary || {};

  const decide = async (kind) => {
    setError(null);
    if (kind !== "approve" && feedback.trim().length < 3) {
      setError("Please write feedback explaining what should change.");
      return;
    }
    setBusy(kind);
    try {
      if (kind === "approve") await Api.approve(executionId, feedback.trim());
      else await Api.reject(executionId, feedback.trim(), kind === "revise");
      setFeedback("");
      setConfirmReject(false);
      onDecided?.();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-white p-5" data-testid="approval-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-amber-100 p-2 text-amber-700">
            <ShieldAlert size={18} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Human approval required</p>
            <h3 className="font-semibold text-slate-900">{CHECKPOINT_LABELS[approval.checkpoint]} checkpoint</h3>
            <p className="text-sm text-slate-600 mt-0.5">{question}</p>
            <p className="text-xs text-slate-400 mt-1">
              {approval.project_name} · execution #{executionId} · requested {timeAgo(approval.created_at)}
            </p>
          </div>
        </div>
        {showLink && (
          <Link to={`${CHECKPOINT_PAGES[approval.checkpoint]}?execution=${executionId}`} className="text-sm font-medium text-violet-700 hover:underline">
            Review details →
          </Link>
        )}
      </div>

      {!compact && Object.keys(summary).length > 0 && (
        <dl className="mt-4 grid grid-cols-1 gap-3 rounded-xl bg-white/70 p-4 ring-1 ring-amber-100 sm:grid-cols-2">
          {Object.entries(summary).map(([key, value]) => (
            <div key={key} className="min-w-0">
              <dt className="text-xs text-slate-400">{humanize(key)}</dt>
              <dd className="text-sm text-slate-800 break-words"><SummaryValue value={value} /></dd>
            </div>
          ))}
        </dl>
      )}

      {canApprove ? (
        <>
          <textarea
            className={`${inputClass} mt-4`}
            rows={2}
            placeholder="Feedback (optional for approval, required for revision or rejection)"
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            aria-label="Approval feedback"
          />
          <ErrorBanner error={error} className="mt-3" />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="success" icon={CheckCircle2} loading={busy === "approve"} disabled={!!busy} onClick={() => decide("approve")}>
              Approve
            </Button>
            <Button variant="warning" icon={RotateCcw} loading={busy === "revise"} disabled={!!busy} onClick={() => decide("revise")}>
              Request revision
            </Button>
            <Button variant="secondary" icon={XCircle} disabled={!!busy} onClick={() => setConfirmReject(true)} className="text-red-600">
              Reject
            </Button>
          </div>
        </>
      ) : (
        <p className="mt-4 text-sm text-slate-500">Only reviewers and admins can decide approvals.</p>
      )}

      <Modal
        open={confirmReject}
        title="Reject and stop the workflow?"
        onClose={() => setConfirmReject(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmReject(false)}>Cancel</Button>
            <Button variant="danger" loading={busy === "reject"} onClick={() => decide("reject")}>Reject workflow</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          Rejecting stops this execution permanently. To send the work back to the agent instead, use <b>Request revision</b>.
        </p>
        <textarea className={`${inputClass} mt-3`} rows={3} placeholder="Reason for rejection (required)" value={feedback}
          onChange={(event) => setFeedback(event.target.value)} aria-label="Rejection reason" />
        <ErrorBanner error={error} className="mt-3" />
      </Modal>
    </div>
  );
}
