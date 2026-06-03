import { Bot, CheckCircle2, ChevronDown, KeyRound, Lock, LogIn, Mail, MailCheck, ShieldCheck, Sparkles, UserRound, UserPlus, UsersRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import AppFooter from "../components/common/AppFooter.jsx";
import { API_BASE_URL, authApi } from "../services/api.js";

const initialForm = {
  full_name: "",
  email: "",
  password: "",
  confirm_password: "",
  otp: "",
};

const adminRoles = new Set(["super_admin", "admin", "moderator"]);

const formatApiError = (error) => {
  const data = error.response?.data;

  if (!error.response) {
    return `Could not reach ${API_BASE_URL}. Check that Django is running and the frontend API URL is correct.`;
  }
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  if (data.non_field_errors?.length) return data.non_field_errors[0];

  const fieldErrors = Object.entries(data || {})
    .map(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join(" ") : String(messages);
      return `${field.replaceAll("_", " ")}: ${text}`;
    })
    .filter(Boolean);

  return fieldErrors.length ? fieldErrors.join(" ") : "Something went wrong. Please check your details and try again.";
};

function AuthPage({ initialAccessRole = "user", initialMode = "login", onAuthSuccess, onRegistrationVerified, onAuthRouteChange }) {
  const [accessRole, setAccessRole] = useState(initialAccessRole);
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState(initialForm);
  const [pendingEmail, setPendingEmail] = useState("");
  const [devOtp, setDevOtp] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  const isRegister = mode === "register";
  const isAdminAccess = accessRole === "admin";
  const hasPendingOtp = Boolean(pendingEmail);

  useEffect(() => {
    if (!hasPendingOtp) {
      setAccessRole(initialAccessRole);
      setMode(initialMode);
    }
  }, [hasPendingOtp, initialAccessRole, initialMode]);

  const passwordMismatch = useMemo(
    () => isRegister && form.confirm_password && form.password !== form.confirm_password,
    [form.confirm_password, form.password, isRegister],
  );

  const updateForm = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: name === "otp" ? value.replace(/\D/g, "").slice(0, 6) : value,
    }));
  };

  const resetAuthStep = () => {
    setError("");
    setNotice("");
    setPendingEmail("");
    setDevOtp("");
    setSuccess(null);
  };

  const switchMode = (nextMode) => {
    setMode(nextMode);
    resetAuthStep();
    onAuthRouteChange?.(accessRole, nextMode);
  };

  const switchAccessRole = (nextAccessRole) => {
    setAccessRole(nextAccessRole);
    resetAuthStep();
    onAuthRouteChange?.(nextAccessRole, mode);
  };

  const enterOtpStep = (data, fallbackEmail) => {
    setPendingEmail(data.email || fallbackEmail);
    setDevOtp(data.dev_otp || "");
    setNotice(
      data.dev_otp
        ? `${data.detail || "OTP generated."} Development OTP is shown below.`
        : data.detail || "Verification code sent. Check your inbox to continue.",
    );
  };

  const requestRegisterOtp = async () => {
    if (form.password !== form.confirm_password) {
      throw new Error("Passwords do not match.");
    }

    const payload = {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      password: form.password,
      confirm_password: form.confirm_password,
      access_role: accessRole,
    };
    const { data } = await authApi.register(payload);
    setForm((current) => ({ ...current, ...payload, otp: "" }));
    if (!data.requires_otp) {
      setPendingEmail("");
      setDevOtp("");
      setSuccess({
        title: data.admin_request_pending ? "Admin Request Sent" : "Request Sent",
        message: data.detail || "Your request was received.",
      });
      return;
    }
    enterOtpStep(data, payload.email);
  };

  const requestLoginOtp = async () => {
    const payload = {
      email: form.email.trim(),
      password: form.password,
      access_role: accessRole,
    };
    const { data } = await authApi.login(payload);
    setForm((current) => ({ ...current, email: payload.email, otp: "" }));
    enterOtpStep(data, payload.email);
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setNotice("");

    try {
      if (hasPendingOtp) {
        const { data } = await authApi.verifyOtp({
          email: pendingEmail,
          otp: form.otp,
        });
        if (!isRegister && isAdminAccess && !adminRoles.has(data.user?.role)) {
          throw new Error("You are not an admin. Admin only access is allowed on this page. Please use User Login or ask the super admin to promote your account.");
        }
        if (isRegister || data.purpose === "register") {
          const message = data.detail || "Registration Successful. Your account has been verified successfully.";
          setSuccess({
            title: "Registration Successful",
            message,
          });
          window.setTimeout(() => onRegistrationVerified?.(data, accessRole), 850);
          return;
        }

        setSuccess({
          title: isAdminAccess ? "Admin Login Successful" : "Login Successful",
          message: `Welcome back, ${data.user.display_name || data.user.username}. OPTIMUS is ready to assist you.`,
        });
        window.setTimeout(() => onAuthSuccess(data, "login"), 850);
        return;
      }

      if (isRegister) {
        await requestRegisterOtp();
      } else {
        await requestLoginOtp();
      }
    } catch (err) {
      setError(err.response ? formatApiError(err) : err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative flex min-h-dvh flex-col overflow-hidden bg-[#050814] px-3 py-5 text-slate-100 sm:px-5 sm:py-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_16%,rgba(34,211,238,0.22),transparent_30%),radial-gradient(circle_at_82%_18%,rgba(168,85,247,0.22),transparent_28%),radial-gradient(circle_at_52%_90%,rgba(16,185,129,0.14),transparent_34%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:44px_44px] opacity-25" />

      <section className="relative z-10 mx-auto flex w-full flex-1 items-center">
        <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_430px] lg:items-center">
          <div className="mx-auto max-w-2xl text-center lg:mx-0 lg:text-left">
            <div className="mb-5 inline-flex h-14 w-14 items-center justify-center rounded-lg border border-cyan-300/30 bg-cyan-300/15 text-cyan-100 shadow-2xl shadow-cyan-950/30 backdrop-blur-xl">
              <Bot size={26} />
            </div>
            <h1 className="text-4xl font-semibold tracking-normal text-white sm:text-6xl">OPTIMUS</h1>
            <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-slate-300 sm:text-lg lg:mx-0">
              A premium AI workspace for conversations, resume intelligence, documentation, memory, and NLP tools.
            </p>
            <div className="mx-auto mt-6 grid max-w-xs gap-3 lg:mx-0">
              {[
                { icon: Sparkles, title: "AI Assistant", text: "Fast, structured answers." },
              ].map(({ icon: Icon, title, text }) => (
                <div key={title} className="rounded-lg border border-white/15 bg-white/[0.07] p-4 text-left shadow-2xl shadow-cyan-950/20 backdrop-blur-2xl">
                  <Icon className="mb-3 text-cyan-200" size={20} />
                  <p className="text-sm font-semibold text-white">{title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-400">{text}</p>
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={submit} className="mx-auto w-full max-w-md rounded-lg border border-white/15 bg-white/[0.08] p-4 shadow-2xl shadow-cyan-950/30 backdrop-blur-2xl sm:p-6 lg:max-w-none">
            <RoleSelect value={accessRole} onChange={switchAccessRole} disabled={hasPendingOtp} />

            <div className="mb-5 flex rounded-lg border border-white/10 bg-white/10 p-1">
              <button
                type="button"
                onClick={() => switchMode("login")}
                className={`flex min-w-0 flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${mode === "login" ? "border border-cyan-300/30 bg-cyan-300/15 text-white shadow-lg shadow-cyan-950/25" : "text-slate-400 hover:bg-white/10 hover:text-white"}`}
              >
                <LogIn size={16} /> {isAdminAccess ? "Admin Login" : "Login"}
              </button>
              <button
                type="button"
                onClick={() => switchMode("register")}
                className={`flex min-w-0 flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${isRegister ? "border border-fuchsia-300/30 bg-fuchsia-300/15 text-white shadow-lg shadow-fuchsia-950/25" : "text-slate-400 hover:bg-white/10 hover:text-white"}`}
              >
                <UserPlus size={16} /> {isAdminAccess ? "Admin Register" : "Register"}
              </button>
            </div>

            {success ? (
              <div className="rounded-lg border border-emerald-300/25 bg-emerald-300/10 p-5 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg border border-emerald-300/30 bg-emerald-300/15 text-emerald-100">
                  <CheckCircle2 size={24} />
                </div>
                <h2 className="text-lg font-semibold text-white">{success.title}</h2>
                <p className="mt-2 text-sm leading-6 text-emerald-100/85">{success.message}</p>
              </div>
            ) : (
              <>
                <div className="space-y-4">
                  {isRegister && !hasPendingOtp && (
                    <Field icon={UserRound} label="Full Name" name="full_name" value={form.full_name} onChange={updateForm} required placeholder="Sridhar M" />
                  )}

                  {!hasPendingOtp && (
                    <Field icon={Mail} label="Email Address" name="email" type="email" value={form.email} onChange={updateForm} required placeholder="you@example.com" />
                  )}

                  {!hasPendingOtp && (
                    <Field icon={Lock} label="Password" name="password" type="password" value={form.password} onChange={updateForm} required minLength={8} placeholder="Minimum 8 characters" />
                  )}

                  {isRegister && !hasPendingOtp && (
                    <Field icon={Lock} label="Confirm Password" name="confirm_password" type="password" value={form.confirm_password} onChange={updateForm} required minLength={8} placeholder="Re-enter password" />
                  )}

                  {passwordMismatch && <p className="text-sm text-rose-300">Passwords do not match.</p>}

                  {hasPendingOtp && (
                    <div className="rounded-md border border-cyan-300/25 bg-cyan-300/10 p-4 shadow-lg shadow-cyan-950/20">
                      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-cyan-100">
                        <MailCheck size={18} /> OTP verification
                      </div>
                      <p className="mb-3 text-sm leading-6 text-cyan-100/80">
                        Verification code sent to <span className="font-semibold text-white">{pendingEmail}</span>. It expires in 10 minutes.
                      </p>
                      {devOtp && (
                        <p className="mb-3 rounded-md border border-white/15 bg-white/10 px-3 py-2 text-sm font-semibold text-white">
                          Development OTP: {devOtp}
                        </p>
                      )}
                      <Field icon={KeyRound} label="Enter OTP Code" name="otp" value={form.otp} onChange={updateForm} required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} placeholder="000000" otp />
                    </div>
                  )}
                </div>

                {notice && <p className="mt-4 rounded-md border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-sm text-cyan-100">{notice}</p>}
                {error && <p className="mt-4 rounded-md border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}

                <button
                  type="submit"
                  disabled={loading || passwordMismatch}
                  className="mt-6 w-full rounded-md border border-cyan-300/40 bg-cyan-300/20 px-4 py-3 text-sm font-semibold text-cyan-50 shadow-lg shadow-cyan-950/25 transition hover:-translate-y-0.5 hover:bg-cyan-300/30 disabled:cursor-not-allowed disabled:translate-y-0 disabled:border-white/10 disabled:bg-white/10 disabled:text-slate-500"
                >
                  {loading ? "Please wait..." : hasPendingOtp ? "Verify OTP" : isRegister ? isAdminAccess ? "Create admin account" : "Create account" : isAdminAccess ? "Send admin login OTP" : "Send login OTP"}
                </button>

                {hasPendingOtp && (
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={async () => {
                        setLoading(true);
                        setError("");
                        try {
                          if (isRegister) await requestRegisterOtp();
                          else await requestLoginOtp();
                        } catch (err) {
                          setError(err.response ? formatApiError(err) : err.message);
                        } finally {
                          setLoading(false);
                        }
                      }}
                      disabled={loading}
                      className="rounded-md border border-white/15 bg-white/10 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-white/15 disabled:opacity-50"
                    >
                      Resend OTP
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPendingEmail("");
                        setDevOtp("");
                        setNotice("");
                        setError("");
                      }}
                      className="rounded-md border border-white/15 bg-white/10 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-white/15"
                    >
                      Edit details
                    </button>
                  </div>
                )}
              </>
            )}
          </form>
        </div>
      </section>

      <AppFooter />
    </main>
  );
}

function Field({ icon: Icon, label, otp = false, ...props }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <div className="mt-1 flex min-h-11 items-center rounded-md border border-white/15 bg-white/10 px-3 text-white transition focus-within:border-cyan-300/60 focus-within:ring-2 focus-within:ring-cyan-300/15">
        <Icon className="mr-2 shrink-0 text-cyan-200" size={18} />
        <input
          {...props}
          className={`auth-field-input min-w-0 flex-1 border-0 p-0 text-sm text-white outline-none placeholder:text-slate-500 ${otp ? "tracking-[0.28em]" : ""}`}
        />
      </div>
    </label>
  );
}

function RoleSelect({ value, onChange, disabled }) {
  const Icon = value === "admin" ? ShieldCheck : UsersRound;

  return (
    <label className="mb-4 block">
      <span className="text-sm font-medium text-slate-300">Role</span>
      <div className={`mt-1 flex min-h-12 items-center rounded-md border px-3 text-white transition ${value === "admin" ? "border-amber-300/35 bg-amber-300/15 shadow-lg shadow-amber-950/20" : "border-cyan-300/30 bg-cyan-300/15 shadow-lg shadow-cyan-950/20"} ${disabled ? "opacity-60" : "focus-within:ring-2 focus-within:ring-cyan-300/15"}`}>
        <Icon className={`mr-2 shrink-0 ${value === "admin" ? "text-amber-100" : "text-cyan-100"}`} size={18} />
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          className="auth-field-input min-w-0 flex-1 appearance-none border-0 p-0 text-sm font-semibold text-white outline-none disabled:cursor-not-allowed"
        >
          <option className="bg-slate-950 text-white" value="user">User</option>
          <option className="bg-slate-950 text-white" value="admin">Admin</option>
        </select>
        <ChevronDown className="ml-2 shrink-0 text-slate-300" size={17} />
      </div>
    </label>
  );
}

export default AuthPage;
