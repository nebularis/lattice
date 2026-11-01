// SPDX-License-Identifier: MPL-2.0
import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import { completeSignIn, loadSession, type Session } from "./session";
import { SessionContext, SignIn } from "./ui/Session";
import { Vocabulary } from "./rdf/vocabulary";
import { Home } from "./ui/Home";
import { Spinner, useRoute } from "./ui/kit";
import { Workspace } from "./ui/Workspace";
import "./styles.css";

function App() {
  const route = useRoute();
  const [vocab, setVocab] = useState<Vocabulary>();
  const [session, setSession] = useState<Session>();
  const [error, setError] = useState<string>();
  useEffect(() => {
    // Coming back from the provider, the code is exchanged before anything else asks the service.
    loadSession()
      .then(async (s) => ((await completeSignIn(s)) ? loadSession() : s))
      .then((s) => {
        setSession(s);
        if (!s.principal) return;
        return api.vocabulary().then((text) => setVocab(Vocabulary.parse(text)));
      })
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
  if (!session) {
    return (
      <div className="empty" style={{ height: "100%" }}>
        <Spinner size={22} />
      </div>
    );
  }
  if (!session.principal) return <SignIn session={session} />;
  return (
    <SessionContext.Provider value={session}>
      <StartWarnings />
      <Page route={route} vocab={vocab} />
    </SessionContext.Provider>
  );
}

/** The warnings of the service's start, such as a promotion contract out of date, shown until dismissed (PM-Q3). */
function StartWarnings() {
  const [warnings, setWarnings] = useState<string[]>([]);
  useEffect(() => {
    void api.warnings().then(setWarnings);
  }, []);
  if (warnings.length === 0) return null;
  return (
    <div className="construction start-warnings" role="status">
      <div className="grow">
        <strong>The studio's start had warnings</strong>
        {warnings.map((w) => (
          <div key={w} className="small">{w}</div>
        ))}
      </div>
      <button className="btn ghost sm" onClick={() => setWarnings([])}>Dismiss</button>
    </div>
  );
}

function Page({ route, vocab }: { route: string[]; vocab?: Vocabulary }) {
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
