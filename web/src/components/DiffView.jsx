// Unified diff, coloured per line. Header lines (diff --git, index, ---/+++) are hidden.
export default function DiffView({ diff }) {
  if (!diff) return <div className="muted small">No changes in this file.</div>;
  const lines = diff.split("\n").filter(l =>
    !/^(diff --git|index |--- |\+\+\+ |new file mode|deleted file mode|similarity|rename )/.test(l));
  return (
    <div className="diff">
      {lines.map((l, i) => {
        const cls = l.startsWith("@@") ? "hunk" : l.startsWith("+") ? "add" : l.startsWith("-") ? "del" : "";
        return <pre key={i} className={cls}>{l || " "}</pre>;
      })}
    </div>
  );
}
