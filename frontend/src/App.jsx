import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import AuthPage from "./pages/AuthPage.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import Toast from "./components/common/Toast.jsx";
import { authApi, clearStoredTokens, getStoredAuthUser, storeAuthSession, storeAuthUser } from "./services/api.js";

const adminRoles = new Set(["super_admin", "admin", "moderator"]);
const defaultSignedInPath = (nextUser) => (adminRoles.has(nextUser?.role) ? "/admin" : "/chat");
const authRoutes = new Set(["/login", "/register", "/admin/login", "/admin/register"]);
const authPath = (accessRole, mode) => {
  if (accessRole === "admin") {
    return mode === "register" ? "/admin/register" : "/admin/login";
  }

  return mode === "register" ? "/register" : "/login";
};

const AdminRoute = ({ user, children }) => {
  if (!user || !adminRoles.has(user.role)) {
    return <AdminAccessDenied user={user} />;
  }

  return children;
};

const ProtectedRoute = ({ user, redirectTo = "/login", children }) => {
  if (!user) {
    return <Navigate to={redirectTo} replace />;
  }

  return children;
};

const AuthRoute = ({ user, children }) => {
  if (user) {
    return <Navigate to={defaultSignedInPath(user)} replace />;
  }

  return children;
};

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [authEvent, setAuthEvent] = useState(null);
  const [toast, setToast] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const storedUser = getStoredAuthUser();
    if (storedUser) {
      setUser(storedUser);
    }
    if (!storedUser && authRoutes.has(window.location.pathname)) {
      setCheckingAuth(false);
      return;
    }

    authApi
      .me()
      .then(({ data }) => {
        storeAuthUser(data);
        setUser(data);
        if (
          window.location.pathname === "/" ||
          window.location.pathname === "/login" ||
          window.location.pathname === "/register" ||
          window.location.pathname === "/admin/login" ||
          window.location.pathname === "/admin/register"
        ) {
          navigate(defaultSignedInPath(data));
        }
      })
      .catch(() => {
        clearStoredTokens();
        setUser(null);
      })
      .finally(() => setCheckingAuth(false));
  }, [navigate]);

  useEffect(() => {
    if (!user) return;
    if (
      location.pathname === "/" ||
      location.pathname === "/login" ||
      location.pathname === "/register" ||
      location.pathname === "/admin/login" ||
      location.pathname === "/admin/register"
    ) {
      navigate(defaultSignedInPath(user));
      return;
    }
  }, [location.pathname, navigate, user]);

  useEffect(() => {
    const handleExpiredAuth = () => {
      clearStoredTokens();
      setUser(null);
    };

    window.addEventListener("auth:expired", handleExpiredAuth);
    return () => window.removeEventListener("auth:expired", handleExpiredAuth);
  }, []);

  const handleAuthSuccess = (authPayload, eventType = "login") => {
    const nextUser = authPayload.user;
    storeAuthSession(authPayload);
    setUser(nextUser);
    setAuthEvent(eventType);
    navigate(defaultSignedInPath(nextUser));
    setToast({
      title: eventType === "register" ? "Registration Successful" : "Login Successful",
      message: eventType === "register"
        ? `Welcome to OPTIMUS, ${nextUser.display_name || nextUser.username}. Your account has been verified successfully.`
        : `Welcome back, ${nextUser.display_name || nextUser.username}. OPTIMUS is ready to assist you.`,
    });
  };

  const handleRegistrationVerified = (_authPayload, accessRole = "user") => {
    clearStoredTokens();
    setUser(null);
    setAuthEvent(null);
    setToast({
      title: "Registration Successful",
      message: "Registration Successful. Your account has been verified successfully.",
    });
    window.setTimeout(() => {
      navigate(authPath(accessRole, "login"));
    }, 900);
  };

  const handleUserUpdate = (nextUser) => {
    storeAuthUser(nextUser);
    setUser(nextUser);
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      clearStoredTokens();
      setUser(null);
      navigate("/login");
    }
  };

  if (checkingAuth) {
    return (
      <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050814]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(20,184,166,0.25),transparent_32%),radial-gradient(circle_at_82%_18%,rgba(99,102,241,0.28),transparent_28%)]" />
        <div className="relative rounded-lg border border-white/15 bg-white/[0.08] px-4 py-3 text-sm font-medium text-cyan-100 shadow-2xl shadow-cyan-950/30 backdrop-blur-2xl">
          Loading OPTIMUS..
        </div>
      </main>
    );
  }

  return (
    <>
      <Routes>
        <Route
          path="/login"
          element={
            <AuthRoute user={user}>
              <AuthPage
                initialAccessRole="user"
                initialMode="login"
                onAuthSuccess={handleAuthSuccess}
                onRegistrationVerified={handleRegistrationVerified}
                onAuthRouteChange={(nextAccessRole, nextMode) => navigate(authPath(nextAccessRole, nextMode))}
              />
            </AuthRoute>
          }
        />
        <Route
          path="/register"
          element={
            <AuthRoute user={user}>
              <AuthPage
                initialAccessRole="user"
                initialMode="register"
                onAuthSuccess={handleAuthSuccess}
                onRegistrationVerified={handleRegistrationVerified}
                onAuthRouteChange={(nextAccessRole, nextMode) => navigate(authPath(nextAccessRole, nextMode))}
              />
            </AuthRoute>
          }
        />
        <Route
          path="/admin/login"
          element={
            <AuthRoute user={user}>
              <AuthPage
                initialAccessRole="admin"
                initialMode="login"
                onAuthSuccess={handleAuthSuccess}
                onRegistrationVerified={handleRegistrationVerified}
                onAuthRouteChange={(nextAccessRole, nextMode) => navigate(authPath(nextAccessRole, nextMode))}
              />
            </AuthRoute>
          }
        />
        <Route
          path="/admin/register"
          element={
            <AuthRoute user={user}>
              <AuthPage
                initialAccessRole="admin"
                initialMode="register"
                onAuthSuccess={handleAuthSuccess}
                onRegistrationVerified={handleRegistrationVerified}
                onAuthRouteChange={(nextAccessRole, nextMode) => navigate(authPath(nextAccessRole, nextMode))}
              />
            </AuthRoute>
          }
        />
        <Route path="/" element={<Navigate to={user ? defaultSignedInPath(user) : "/login"} replace />} />
        <Route
          path="/chat"
          element={
            <ProtectedRoute user={user}>
              <ChatPage user={user} onLogout={handleLogout} onUserUpdate={handleUserUpdate} authEvent={authEvent} onNavigate={navigate} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute user={user} redirectTo="/admin/login">
              <AdminRoute user={user}>
                <AdminDashboard user={user} onLogout={handleLogout} onNavigate={navigate} />
              </AdminRoute>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={user ? defaultSignedInPath(user) : "/login"} replace />} />
      </Routes>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </>
  );
}

function AdminAccessDenied({ user }) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050814] px-4 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_18%,rgba(20,184,166,0.2),transparent_32%),radial-gradient(circle_at_78%_22%,rgba(245,158,11,0.2),transparent_28%)]" />
      <section className="relative w-full max-w-md rounded-lg border border-amber-300/25 bg-white/[0.08] p-6 text-center shadow-2xl shadow-amber-950/20 backdrop-blur-2xl">
        <h1 className="text-xl font-semibold text-white">Admin Only Access</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          You are not an admin. This page is only for super admin, admin, and moderator accounts.
        </p>
        <p className="mt-3 text-sm leading-6 text-amber-100/85">
          Signed in as {user?.email || "a normal user"}. Please ask the super admin to promote this mail ID if you need admin access.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <a href="/chat" className="rounded-md border border-cyan-300/30 bg-cyan-300/15 px-4 py-2.5 text-sm font-semibold text-cyan-50 transition hover:bg-cyan-300/25">
            Go to Chat
          </a>
          <a href="/admin/login" className="rounded-md border border-white/15 bg-white/10 px-4 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-white/15">
            Admin Login
          </a>
        </div>
      </section>
    </main>
  );
}

export default App;
