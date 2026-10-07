import { timeAgo } from "../meta.js";

// Compact "which repository is this" line: name, branch, remote or local, uncommitted changes
export function RepoLine({ repo, path }) {
  if (!repo) return <span className="muted small">📁 {path ?? "folder"} · not a git repository</span>;
  return (
    <span className="repo-line">
      <b>{repo.name}</b>
      {repo.branch && <span className="branch">⎇ {repo.branch}</span>}
      {repo.web ? <a href={repo.web} target="_blank" rel="noreferrer">{repo.web.replace("https://", "")} ↗</a>
        : repo.remote ? <span className="mono small">{repo.remote}</span>
          : <span className="muted small">local only</span>}
      {repo.uncommitted > 0 && <span className="badge b-warn" title="Uncommitted changes in this repository">{repo.uncommitted} uncommitted</span>}
    </span>
  );
}

export function RepoCard({ title, repo, path, children }) {
  return (
    <div className="repo-card">
      <div className="repo-card-head">
        <div className="grow">
          <div className="repo-title">{title}</div>
          <RepoLine repo={repo} path={path} />
        </div>
        {children}
      </div>
      <div className="repo-meta">
        <span className="mono small">{repo?.display_root ?? path}{repo?.subdir ? ` (folder ${repo.subdir})` : ""}</span>
        {repo?.head && <span className="muted small">last commit <span className="mono">{repo.head.sha}</span> “{repo.head.subject}” · {timeAgo(repo.head.date)}</span>}
      </div>
    </div>
  );
}
