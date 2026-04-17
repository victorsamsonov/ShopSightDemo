import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import IntroPage from "./pages/IntroPage";
import ChatPage from "./pages/ChatPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IntroPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

