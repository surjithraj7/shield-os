export default function Toasts({ toasts, onDismiss }) {
  return (
    <div className="toast-area">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.cls || ""}`} onClick={() => onDismiss(t.id)}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}
