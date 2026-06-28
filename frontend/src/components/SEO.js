import { Helmet } from "react-helmet-async";

/**
 * SEO — reusable per-page meta tag manager.
 *
 * Renders unique <title>, <meta description>, canonical, and Open Graph tags
 * for every route. Crawlers that execute JS (Googlebot, Bingbot, Semrush) will
 * see the updated tags; legacy bots see the defaults from public/index.html.
 *
 * Usage:
 *   <SEO
 *     title="Pricing — Ascendra Academy"
 *     description="Three plans..."
 *     path="/pricing"
 *   />
 */
export default function SEO({
  title,
  description,
  path = "",
  image = "https://ascendraacademy.com/og-default.png",
  type = "website",
  noindex = false,
}) {
  const url = `https://ascendraacademy.com${path}`;
  const fullTitle = title?.includes("Ascendra") ? title : `${title} · Ascendra Academy`;
  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={url} />
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      <meta property="og:type" content={type} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={url} />
      <meta property="og:image" content={image} />
      <meta property="og:site_name" content="Ascendra Academy" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />
    </Helmet>
  );
}
