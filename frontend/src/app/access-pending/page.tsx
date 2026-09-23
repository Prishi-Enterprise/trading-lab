import { Brand } from "@/components/brand";

export default function AccessPending() {
  return (
    <main className="simple-page">
      <div className="simple-card">
        <Brand />
        <span className="badge">Access pending</span>
        <h1>This email is not on the Trading Lab access list.</h1>
        <p>Sign out and use the invited Prishi email, or add this address as a Trading Lab member.</p>
        <form action="/auth/signout" method="post"><button className="primary-button">Sign out</button></form>
      </div>
    </main>
  );
}
