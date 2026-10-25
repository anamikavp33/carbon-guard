import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, me, setToken, clearToken } from "../api.js";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await login(email.trim(), password);
      setToken(data.access_token);
      const profile = await me();
      if (profile.role !== "admin") {
        clearToken();
        throw new Error("This account is not an administrator. Use the mobile app instead.");
      }
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={handleSubmit}>
        <div className="brand"><span className="leaf" aria-hidden="true">&#127807;</span> Carbon Guard</div>
        <p className="muted">Administrator sign in</p>
        <label htmlFor="email">Email</label>
        <input id="email" value={email} onChange={(e) => setEmail(e.target.value)} type="email"
               autoComplete="username" required />
        <label htmlFor="password">Password</label>
        <input id="password" value={password} onChange={(e) => setPassword(e.target.value)} type="password"
               autoComplete="current-password" required />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn full" disabled={busy}>{busy ? "Signing in..." : "Sign in"}</button>
      </form>
    </div>
  );
}
