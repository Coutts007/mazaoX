import { useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, errorMessage } from "../../api/client";
import { Modal } from "../../components/Modal";
import { TextAreaField } from "../../components/Field";

/** Filters and the page number live in the URL so views can be bookmarked and survive reloads. */
export function useUrlState() {
  const [params, setParams] = useSearchParams();
  const get = (k: string) => params.get(k) ?? "";
  const set = (patch: Record<string, string | null>) => {
    const n = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) (v ? n.set(k, v) : n.delete(k));
    if (!("page" in patch)) n.delete("page");
    setParams(n, { replace: true });
  };
  return { get, set, page: Number(params.get("page") ?? "1") || 1 };
}

interface ReasonProps {
  title: string;
  confirmLabel: string;
  intro?: ReactNode;
  /** Label of the free-text field. */
  label?: string;
  required?: boolean;
  danger?: boolean;
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
}

/** Confirmation dialog that captures the reason for a sensitive admin action (the reason is written to the audit log). */
export function ReasonDialog({ title, confirmLabel, intro, label = "Reason", required = false, danger = false, onConfirm, onClose }: ReasonProps) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | undefined>();
  async function go() {
    if (required && !reason.trim()) { setErr(`${label} is required.`); return; }
    setBusy(true);
    setErr(undefined);
    try { await onConfirm(reason.trim()); onClose(); }
    catch (x) { setErr(x instanceof ApiError && x.fieldErrors.reason ? x.fieldErrors.reason : errorMessage(x)); setBusy(false); }
  }
  return (
    <Modal title={title} onClose={onClose} footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} disabled={busy} onClick={go}>{busy ? "Working…" : confirmLabel}</button></>}>
      <div className="stack">
        {intro}
        <TextAreaField label={label} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} error={err} />
      </div>
    </Modal>
  );
}

export const STATUS_BADGE: Record<string, string> = {
  open: "b-bad", investigating: "b-low", resolved: "b-ok", dismissed: "b-off",
  pending: "b-low", dispatched: "b-low", delivered: "b-ok", failed: "b-bad",
};
