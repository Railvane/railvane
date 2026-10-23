import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

// In-app dialogs instead of window.confirm / prompt / alert: same look as the rest of Railvane,
// Escape cancels, Enter confirms, focus lands on the input or the confirm button.
//
//   const dialog = useDialog();
//   if (await dialog.confirm({ title, message, confirmLabel, danger })) { … }
//   const why = await dialog.prompt({ title, message, label, placeholder });   // null when cancelled
//   await dialog.tell({ title, message });                                      // errors, notices
const DialogContext = createContext(null);

export function useDialog() {
  return useContext(DialogContext);
}

function DialogBox({ spec, onClose }) {
  const [value, setValue] = useState(spec.initial ?? "");
  const focusRef = useRef(null);
  useEffect(() => { focusRef.current?.focus(); }, []);

  const isPrompt = spec.kind === "prompt";
  const canConfirm = !isPrompt || !spec.required || value.trim();
  const confirm = () => canConfirm && onClose(isPrompt ? value.trim() : true);
  const cancel = () => onClose(spec.kind === "tell" ? true : isPrompt ? null : false);

  const onKey = e => {
    if (e.key === "Escape") { e.stopPropagation(); cancel(); }
    if (e.key === "Enter" && !(e.target.tagName === "TEXTAREA" && e.shiftKey)) { e.preventDefault(); confirm(); }
  };

  return (
    <div className="modal-bg on" onMouseDown={e => e.target === e.currentTarget && cancel()} onKeyDown={onKey}>
      <div className="modal small dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div id="dialog-title" className="title">{spec.title}</div>
        {spec.message && <div className="muted dialog-message">{spec.message}</div>}
        {isPrompt && (
          <label className="dialog-field">
            {spec.label && <span className="muted small">{spec.label}</span>}
            <input ref={focusRef} value={value} placeholder={spec.placeholder ?? ""} onChange={e => setValue(e.target.value)} />
          </label>
        )}
        <div className="dialog-actions">
          {spec.kind !== "tell" && <button className="btn ghost" onClick={cancel}>{spec.cancelLabel ?? "Cancel"}</button>}
          <button ref={isPrompt ? null : focusRef} className={`btn ${spec.danger ? "danger" : "primary"}`}
            disabled={!canConfirm} onClick={confirm}>{spec.confirmLabel ?? "OK"}</button>
        </div>
      </div>
    </div>
  );
}

export function DialogProvider({ children }) {
  const [spec, setSpec] = useState(null);

  const open = useCallback(kind => options => new Promise(resolve => setSpec({ ...options, kind, resolve })), []);
  const [api] = useState(() => ({ confirm: open("confirm"), prompt: open("prompt"), tell: open("tell") }));

  const close = result => {
    spec.resolve(result);
    setSpec(null);
  };

  return (
    <DialogContext.Provider value={api}>
      {children}
      {spec && <DialogBox key={spec.title + spec.kind} spec={spec} onClose={close} />}
    </DialogContext.Provider>
  );
}
