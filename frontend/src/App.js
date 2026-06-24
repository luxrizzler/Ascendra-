import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Toaster } from "sonner";
import "@/index.css";
import { AuthProvider } from "@/context/AuthContext";
import WebNav from "@/components/WebNav";
import WebFooter from "@/components/WebFooter";
import RequireAuth from "@/components/RequireAuth";

import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Paths from "@/pages/Paths";
import PathDetail from "@/pages/PathDetail";
import LessonPlayer from "@/pages/LessonPlayer";
import Tutor from "@/pages/Tutor";
import Models from "@/pages/Models";
import Profile from "@/pages/Profile";
import Pricing from "@/pages/Pricing";
import CheckoutSuccess from "@/pages/CheckoutSuccess";
import Certificate from "@/pages/Certificate";
import Admin from "@/pages/Admin";
import AdminCurriculum from "@/pages/AdminCurriculum";
import AdminCurriculumEdit from "@/pages/AdminCurriculumEdit";
import AdminStudio from "@/pages/AdminStudio";
import AuthCallback from "@/pages/AuthCallback";
import NotFound from "@/pages/NotFound";
import { api } from "@/lib/api";

function ScrollToTop() {
  const loc = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);
  return null;
}

function PageviewTracker() {
  const loc = useLocation();
  useEffect(() => {
    api.post("/track/pageview", { path: loc.pathname, referrer: document.referrer || "" }).catch(() => {});
  }, [loc.pathname]);
  return null;
}

function Shell() {
  const loc = useLocation();
  const hideNav = loc.pathname.startsWith("/lessons/") || loc.pathname.startsWith("/certificate/") || loc.pathname.startsWith("/auth/callback");
  return (
    <div className="min-h-screen flex flex-col">
      {!hideNav && <WebNav />}
      <main className="flex-1 fade-up">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
          <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="/paths" element={<RequireAuth><Paths /></RequireAuth>} />
          <Route path="/paths/:pathId" element={<RequireAuth><PathDetail /></RequireAuth>} />
          <Route path="/lessons/:lessonId" element={<RequireAuth><LessonPlayer /></RequireAuth>} />
          <Route path="/tutor" element={<RequireAuth><Tutor /></RequireAuth>} />
          <Route path="/models" element={<RequireAuth><Models /></RequireAuth>} />
          <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
          <Route path="/checkout-success" element={<RequireAuth><CheckoutSuccess /></RequireAuth>} />
          <Route path="/certificate/:certId" element={<RequireAuth><Certificate /></RequireAuth>} />
          <Route path="/admin" element={<RequireAuth admin><Admin /></RequireAuth>} />
          <Route path="/admin/curriculum" element={<RequireAuth admin><AdminCurriculum /></RequireAuth>} />
          <Route path="/admin/curriculum/:pathId" element={<RequireAuth admin><AdminCurriculumEdit /></RequireAuth>} />
          <Route path="/admin/studio" element={<RequireAuth admin><AdminStudio /></RequireAuth>} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      {!hideNav && <WebFooter />}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ScrollToTop />
        <PageviewTracker />
        <Toaster theme="dark" position="top-right" toastOptions={{ style: { background: "#15102B", color: "#fff", border: "1px solid rgba(191,180,255,0.18)" } }} />
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  );
}
