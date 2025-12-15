import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Graph from "./pages/graph/Graph.jsx";
import Info from "./pages/Info/Info.jsx";

import "./styles/reset.css";
import "./styles/theme.css";
import "./styles/globals.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Info />} />
        <Route path="/graph" element={<Graph />} />
        <Route path="*" element={<Info />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
