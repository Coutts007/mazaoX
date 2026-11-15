import { EmptyState } from "../components/Feedback";

export function NotFound() {
  return <div className="wrap"><EmptyState icon="🔍" title="We couldn't find that page" action={{ to: "/", label: "Back to home" }}>The link may be old, or the page may have moved.</EmptyState></div>;
}

export function Forbidden() {
  return <div className="wrap"><EmptyState icon="🔒" title="That area isn't for your account" action={{ to: "/", label: "Back to home" }}>Log in with a different account type to see it.</EmptyState></div>;
}
