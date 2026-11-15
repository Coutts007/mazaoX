import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="center-note" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function Skeleton({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden="true" />;
}

export function EmptyState({ icon = "🌱", title, children, action }: { icon?: string; title: string; children?: ReactNode; action?: { to: string; label: string } }) {
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden="true">{icon}</div>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action && <Link className="btn btn-primary" to={action.to}>{action.label}</Link>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="empty" role="alert">
      <div className="empty-icon" aria-hidden="true">⚠️</div>
      <h3>That didn't work</h3>
      <p>{message}</p>
      {onRetry && <button className="btn btn-ghost" onClick={onRetry}>Try again</button>}
    </div>
  );
}
