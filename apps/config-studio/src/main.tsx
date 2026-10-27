// SPDX-License-Identifier: MPL-2.0
import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import { Vocabulary } from "./rdf/vocabulary";
import { Home } from "./ui/Home";
import { Spinner, useRoute } from "./ui/kit";
import { Workspace } from "./ui/Workspace";
import "./styles.css";

function App() {
  const route = useRoute();
  const [vocab, setVocab] = useState<Vocabulary>();
  const [error, setError] = useState<string>();
  useEffect(() => {
    api
      .vocabulary()
      .then((text) => setVocab(Vocabulary.parse(text)))
      .catch((e: Error) => setError(e.message));
  }, []);
  if (error) {
    return (
      <div className="empty" style={{ height: "100%" }}>
        <h3>The studio's service did not answer</h3>
        <p>{error}</p>
      </div>
    );
  }
  if (route[0] !== "w" || !route[1]) return <Home />;
  if (!vocab) {
    return (
      <div className="empty" style={{ height: "100%" }}>
        <Spinner size={22} />
      </div>
    );
  }
  return <Workspace key={route[1]} id={route[1]} route={route.slice(2)} vocab={vocab} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
