import { useId, useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

interface Common {
  label: string;
  error?: string;
  hint?: ReactNode;
}

export function TextField({ label, error, hint, ...props }: Common & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} className="input" aria-invalid={!!error} aria-describedby={error ? `${id}-e` : hint ? `${id}-h` : undefined} {...props} />
      {hint && !error && <span id={`${id}-h`} className="hint">{hint}</span>}
      {error && <span id={`${id}-e`} className="err" role="alert">{error}</span>}
    </div>
  );
}

export function PasswordField({ label, error, hint, ...props }: Common & Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  const id = useId();
  const [show, setShow] = useState(false);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="pw">
        <input id={id} className="input" type={show ? "text" : "password"} aria-invalid={!!error} aria-describedby={error ? `${id}-e` : hint ? `${id}-h` : undefined} {...props} />
        <button type="button" onClick={() => setShow((s) => !s)} aria-pressed={show} aria-label={show ? "Hide password" : "Show password"}>
          {show ? "Hide" : "Show"}
        </button>
      </div>
      {hint && !error && <span id={`${id}-h`} className="hint">{hint}</span>}
      {error && <span id={`${id}-e`} className="err" role="alert">{error}</span>}
    </div>
  );
}

export function SelectField({ label, error, hint, children, ...props }: Common & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} className="select" aria-invalid={!!error} {...props}>{children}</select>
      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="err" role="alert">{error}</span>}
    </div>
  );
}

export function TextAreaField({ label, error, hint, ...props }: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} className="textarea" aria-invalid={!!error} {...props} />
      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="err" role="alert">{error}</span>}
    </div>
  );
}
