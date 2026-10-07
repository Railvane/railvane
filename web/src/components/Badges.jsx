export function VisBadge({ visibility }) {
  return visibility === "shared"
    ? <span className="vis vis-s">👥 shared</span>
    : <span className="vis vis-p">🔒 private</span>;
}

export function Badge({ kind = "muted", children, title }) {
  return <span className={`badge b-${kind}`} title={title}>{children}</span>;
}

export function Dot({ color }) {
  return <span className="dot" style={{ background: color }} />;
}
