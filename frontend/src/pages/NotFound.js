import { Link } from "react-router-dom";
export default function NotFound() {
  return (
    <div className="min-h-[60vh] grid place-items-center px-5">
      <div className="text-center max-w-md">
        <div className="asc-kicker">404</div>
        <h1 className="asc-h2 text-5xl mt-2">This page is not on your path.</h1>
        <p className="text-[var(--asc-text-dim)] mt-3">The page you're looking for doesn't exist. Let's get you back.</p>
        <Link to="/" className="asc-btn-primary mt-6 inline-flex">Back home</Link>
      </div>
    </div>
  );
}
