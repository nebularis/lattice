// SPDX-License-Identifier: MPL-2.0
// The signed-in principal, shown in each page's header, and the page shown before anyone is signed in (ADR-A149).

import { createContext, useContext } from "react";
import { LogIn, LogOut, User } from "lucide-react";
import { chooseLocal, signIn, signOut, type Session } from "../session";

export const SessionContext = createContext<Session | undefined>(undefined);

export const useSession = () => useContext(SessionContext);

/** Who is signed in. A local session switches between its developer principals, an OpenID Connect one signs out. */
export function PrincipalMenu() {
  const session = useSession();
  if (!session?.principal) return null;
  if (session.provider === "local") {
    return (
      <label className="btn ghost sm" title="Signed in locally, for development">
        <User size={14} />
        <select
          aria-label="Signed in as"
          value={session.principal}
          onChange={(e) => chooseLocal(e.target.value)}
          style={{ border: "none", background: "transparent", font: "inherit", color: "inherit" }}
        >
          {(session.principalOption ?? [session.principal]).map((name) => (
            <option key={name} value={name}>
              {name}
              {session.administrator?.includes(name) ? " (administrator)" : ""}
            </option>
          ))}
        </select>
      </label>
    );
  }
  return (
    <button className="btn ghost sm" onClick={signOut} title={`Signed in at ${session.issuer ?? "the provider"}`}>
      <User size={14} /> {session.principal}
      {session.admin ? " (administrator)" : ""} <LogOut size={14} />
    </button>
  );
}

export function SignIn({ session }: { session: Session }) {
  return (
    <div className="empty" style={{ height: "100%" }}>
      <h3>Sign in to the Configuration Studio</h3>
      <p>The studio signs you in at {session.issuer ?? "your organisation's identity provider"}.</p>
      <button className="btn primary" onClick={() => void signIn(session)}>
        <LogIn size={14} /> Sign in
      </button>
    </div>
  );
}
