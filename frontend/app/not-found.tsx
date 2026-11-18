export default function NotFound() {
  return (
    <main role="main" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '2rem' }}>
      <section aria-labelledby="not-found-title">
        <h1 id="not-found-title">Page not found</h1>
        <p>This wedding plan page does not exist.</p>
        <a href="/">Return to your plans</a>
      </section>
    </main>
  );
}
