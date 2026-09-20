import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./studio.css";
import { Studio } from "./studio";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Studio />
  </StrictMode>,
);
