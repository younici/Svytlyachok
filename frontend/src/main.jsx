import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Graph from "./pages/Graph/Graph.jsx";
import Home from "./pages/Home/Home.jsx";
import Info from "./pages/Info/Info.jsx";
import Faq from "./pages/Faq/Faq.jsx";
import Privacy from "./pages/Privacy/Privacy.jsx";
import Widget from "./pages/Widget/Widget.jsx";
import { AdsConsentProvider } from "./context/AdsConsentContext.jsx";

import "./styles/reset.css";
import "./styles/theme.css";
import "./styles/globals.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AdsConsentProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/info" element={<Info />} />
            <Route path="/faq" element={<Faq />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/widget" element={<Widget />}/>
            <Route path="*" element={<Home />} />
          </Route>
        </Routes>
      </AdsConsentProvider>
    </BrowserRouter>
  </StrictMode>
);
