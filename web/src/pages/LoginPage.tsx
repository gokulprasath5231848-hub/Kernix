import { useState, FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { login, isAuthenticated } from '../auth';

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already signed in → skip the login screen (proper redirect, not a
  // navigate() call during render).
  if (isAuthenticated()) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#08080a] text-zinc-100 font-geist antialiased relative flex flex-col justify-between selection:bg-[#ECC246] selection:text-black">
      {/* Ambient background */}
      <div aria-hidden className="fixed inset-0 login-telemetry-grid pointer-events-none z-0" />
      <div aria-hidden className="fixed inset-0 login-gold-spotlight pointer-events-none z-0" />
      <div className="fixed top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#ECC246]/40 to-transparent z-50" />

      {/* Status bar */}
      <header className="relative z-10 w-full pt-5 px-6 md:px-12 flex justify-between items-center text-xs font-mono">
        <div className="flex items-center space-x-2.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#ECC246] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#ECC246]" />
          </span>
          <span className="text-zinc-300 font-medium tracking-wider text-[11px]">
            SYSTEM STATUS: SECURE &amp; ONLINE
          </span>
        </div>
        <div className="text-[11px] text-zinc-500 tracking-wider">NODE PROTOCOL v4.8</div>
      </header>

      {/* Center */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 py-8 sm:px-6">
        {/* Brand */}
        <div className="text-center mb-7 flex flex-col items-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-3xl font-bold text-black drop-shadow-[0_0_25px_rgba(201,162,39,0.4)] login-logo-mark">
            K
          </div>
          <h1 className="text-3xl font-bold tracking-[0.25em] text-white uppercase select-none flex items-center justify-center pl-1">
            <span>KINTI</span>
            <span className="text-[#ECC246] drop-shadow-[0_0_12px_rgba(236,194,70,0.5)]">X</span>
          </h1>
          <div className="mt-2.5 flex items-center justify-center space-x-3 text-xs tracking-[0.2em] font-mono text-[#C9A227]/90 uppercase">
            <span className="h-px w-6 md:w-10 bg-gradient-to-r from-transparent to-[#C9A227]/70" />
            <span>Autonomous Intelligence, Human Control</span>
            <span className="h-px w-6 md:w-10 bg-gradient-to-l from-transparent to-[#C9A227]/70" />
          </div>
        </div>

        {/* Card */}
        <div className="w-full max-w-[440px] relative">
          <div className="absolute -inset-1 bg-gradient-to-b from-[#C9A227]/20 via-[#ECC246]/10 to-transparent rounded-2xl blur-lg pointer-events-none" />
          <div className="relative bg-[#0c0c11]/95 backdrop-blur-xl border border-[#C9A227]/25 rounded-2xl shadow-[0_12px_45px_rgba(0,0,0,0.85)] p-7 md:p-8">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold tracking-tight text-white">Operator Sign In</h2>
              <p className="mt-1 text-xs text-zinc-400">
                Authenticate to access your governance console
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              {/* Email */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-zinc-300 tracking-wide uppercase" htmlFor="email">
                  Work Email
                </label>
                <div className="relative rounded-lg bg-[#14141a] border border-neutral-700 transition duration-200 focus-within:border-[#ECC246] focus-within:ring-1 focus-within:ring-[#ECC246]/40">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-400">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
                    </svg>
                  </div>
                  <input
                    className="w-full pl-10 pr-3.5 py-2.5 bg-transparent border-0 text-white placeholder-zinc-500 text-sm focus:ring-0 rounded-lg outline-none"
                    id="email"
                    name="email"
                    placeholder="operator@kintix.ai"
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="username"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-zinc-300 tracking-wide uppercase" htmlFor="password">
                    Access Key / Password
                  </label>
                </div>
                <div className="relative rounded-lg bg-[#14141a] border border-neutral-700 transition duration-200 focus-within:border-[#ECC246] focus-within:ring-1 focus-within:ring-[#ECC246]/40">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-400">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
                    </svg>
                  </div>
                  <input
                    className="w-full pl-10 pr-10 py-2.5 bg-transparent border-0 text-white placeholder-zinc-500 text-sm focus:ring-0 rounded-lg outline-none tracking-widest"
                    id="password"
                    name="password"
                    placeholder="••••••••••••"
                    required
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                  <button
                    aria-label="Toggle password view"
                    className={`absolute inset-y-0 right-0 pr-3 flex items-center transition-colors ${showPassword ? 'text-[#ECC246]' : 'text-zinc-400'} hover:text-[#ECC246]`}
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
                      <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                  {error}
                </div>
              )}

              {/* Row */}
              <div className="flex items-center justify-between pt-1 text-xs">
                <span className="text-zinc-400">Session lasts 12 hours</span>
                <div className="flex items-center space-x-1 text-zinc-500 font-mono text-[11px]">
                  <svg className="w-3.5 h-3.5 text-[#ECC246]/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                  </svg>
                  <span>Encrypted transport</span>
                </div>
              </div>

              {/* CTA */}
              <div className="pt-2">
                <button
                  className="w-full login-btn-gold text-black font-semibold tracking-wider text-xs md:text-sm py-3.5 px-4 rounded-lg flex items-center justify-center gap-2 uppercase group cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
                  type="submit"
                  disabled={submitting}
                >
                  <span>{submitting ? 'Authenticating…' : 'Sign in to console'}</span>
                  {!submitting && (
                    <svg className="w-4 h-4 text-black transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" />
                    </svg>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full py-4 px-6 md:px-12 border-t border-zinc-900/90 bg-[#070709]/80 backdrop-blur">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-3 text-xs text-zinc-500">
          <span>KINTIX © 2025 Sovereign Autonomous Systems Inc.</span>
          <span className="font-mono text-[11px]">Governance Console</span>
        </div>
      </footer>
    </div>
  );
}
