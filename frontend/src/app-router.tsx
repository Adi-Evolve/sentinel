import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "@/App";
import AboutLogSentinelPage from "@/pages/about-log-sentinel";
import DemoOne from "@/pages/demo";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DemoOne />} />
        <Route path="/dashboard/*" element={<App />} />
        <Route path="/about" element={<AboutLogSentinelPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
