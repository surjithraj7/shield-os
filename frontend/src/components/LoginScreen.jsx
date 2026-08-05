import { useState } from "react";
import { ENDPOINTS, getJSON, setAuthToken } from "../api";

const LANGS = {
  en: { name: "EN", rtl: false },
  ta: { name: "தமிழ்", rtl: false },
  hi: { name: "हिन्दी", rtl: false },
  zh: { name: "中文", rtl: false },
  ar: { name: "عربي", rtl: true },
  fr: { name: "FR", rtl: false }
};

const T = {
  en: {
    title: "SHIELD-OS",
    sub: "DIGITAL CYBER TWIN // MISSION CONTROL",
    user: "OPERATOR ID",
    pass: "ACCESS KEY",
    login: "LOGIN",
    busy: "AUTHENTICATING...",
    guest: "ENTER AS GUEST (OFFLINE SIM)",
    hint: "DEMO ACCESS: admin / admin123 | operator / shield123",
    error: "ACCESS DENIED - INVALID CREDENTIALS",
    lang: "LANGUAGE"
  },
  ta: {
    title: "SHIELD-OS",
    sub: "டிஜிட்டல் சைபர் ட்வின் // கட்டுப்பாட்டு மையம்",
    user: "இயக்குநர் அடையாளம்",
    pass: "அணுகு விசை",
    login: "உள்நுழை",
    busy: "சரிபார்க்கிறது...",
    guest: "விருந்தினராக நுழை (ஆஃப்லைன் சிம்)",
    hint: "மாதிரி அணுகல்: admin / admin123 | operator / shield123",
    error: "அணுகல் மறுக்கப்பட்டது - தவறான சான்றுகள்",
    lang: "மொழி"
  },
  hi: {
    title: "SHIELD-OS",
    sub: "डिजिटल साइबर ट्विन // मिशन नियंत्रण",
    user: "संचालक आईडी",
    pass: "पहुंच कुंजी",
    login: "लॉगिन",
    busy: "सत्यापन हो रहा है...",
    guest: "अतिथि के रूप में दर्ज करें (ऑफ़लाइन सिम)",
    hint: "डेमो एक्सेस: admin / admin123 | operator / shield123",
    error: "पहुंच अस्वीकृत - अमान्य प्रमाण",
    lang: "भाषा"
  },
  zh: {
    title: "SHIELD-OS",
    sub: "数字孪生 // 任务控制中心",
    user: "操作员编号",
    pass: "访问密钥",
    login: "登录",
    busy: "验证中...",
    guest: "以访客身份进入（离线模拟）",
    hint: "演示访问: admin / admin123 | operator / shield123",
    error: "访问被拒绝 - 凭据无效",
    lang: "语言"
  },
  ar: {
    title: "SHIELD-OS",
    sub: "التوأم الرقمي // مركز التحكم",
    user: "معرف المشغل",
    pass: "مفتاح الوصول",
    login: "تسجيل الدخول",
    busy: "جارٍ التحقق...",
    guest: "الدخول كضيف (محاكاة دون اتصال)",
    hint: "وصول تجريبي: admin / admin123 | operator / shield123",
    error: "تم رفض الوصول - بيانات اعتماد غير صالحة",
    lang: "اللغة"
  },
  fr: {
    title: "SHIELD-OS",
    sub: "JUMEAU NUMÉRIQUE // CENTRE DE MISSION",
    user: "ID OPÉRATEUR",
    pass: "CLÉ D'ACCÈS",
    login: "CONNEXION",
    busy: "AUTHENTIFICATION...",
    guest: "ENTRER COMME INVITÉ (SIM HORS LIGNE)",
    hint: "ACCÈS DÉMO: admin / admin123 | operator / shield123",
    error: "ACCÈS REFUSÉ - IDENTIFIANTS INVALIDES",
    lang: "LANGUE"
  }
};

export default function LoginScreen({ onAuth, onGuest }) {
  const [lang, setLang] = useState(() => localStorage.getItem("shield_lang") || "en");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const t = T[lang] || T.en;

  function chooseLang(code) {
    setLang(code);
    localStorage.setItem("shield_lang", code);
  }

  async function login(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await getJSON(ENDPOINTS.login, {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password })
      });
      setAuthToken(res.token);
      onAuth({ username: res.username, role: res.role, full_name: res.full_name });
    } catch (err) {
      setError(t.error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="wallpaper" />
      <form className="login-box" onSubmit={login} dir={LANGS[lang].rtl ? "rtl" : "ltr"}>
        <div className="login-logo">{t.title}</div>
        <div className="login-sub">{t.sub}</div>
        <div className="login-line" />

        <label className="login-label" htmlFor="login-user">{t.user}</label>
        <input
          id="login-user"
          className="login-input"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          spellCheck={false}
        />
        <label className="login-label" htmlFor="login-pass">{t.pass}</label>
        <input
          id="login-pass"
          className="login-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />

        {error && <div className="login-error">{error}</div>}

        <button className="btn chunky login-btn" type="submit" disabled={busy}>
          {busy ? t.busy : t.login}
        </button>
        <button className="btn chunky login-guest" type="button" onClick={onGuest}>
          {t.guest}
        </button>

        <div className="login-lang">
          <span className="login-lang-label">{t.lang}:</span>
          {Object.entries(LANGS).map(([code, meta]) => (
            <button
              key={code}
              type="button"
              className={`login-lang-btn ${code === lang ? "active" : ""}`}
              onClick={() => chooseLang(code)}
              title={code}
            >
              {meta.name}
            </button>
          ))}
        </div>

        <div className="login-hint">{t.hint}</div>
      </form>
    </div>
  );
}
