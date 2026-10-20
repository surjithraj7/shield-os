import { useEffect, useState } from "react";

function pad(n) {
  return (n < 10 ? "0" : "") + n;
}

export default function Taskbar({ windows, onToggle, sysMsg, user, onLogout }) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const openWins = windows.filter((w) => w.open);

  return (
    <footer className="taskbar">
      <button className="start-btn">&#9670; SHIELD-OS</button>
      <div className="taskbar-tasks">
        {openWins.map((w) => (
          <button
            key={w.id}
            className={`task-tab ${w.minimized ? "" : "active"}`}
            onClick={() => onToggle(w.id)}
          >
            {w.title}
          </button>
        ))}
      </div>
      <div className="taskbar-right">
        <span className="sys-msg">SYS: {sysMsg}</span>
        {user && (
          <span className="taskbar-user">
            {user.username} [{user.role}]
            <button className="btn chunky logout-btn" onClick={onLogout}>LOGOUT</button>
          </span>
        )}
        <span>{`${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`}</span>
      </div>
    </footer>
  );
}
