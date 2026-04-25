/**
 * Inline pre-hydration script that sets `dark` class on <html> before paint.
 * Source of truth: localStorage["theme"] = "light" | "dark", else system pref.
 * Avoids the dreaded flash-of-wrong-theme.
 */
export function ThemeScript() {
  const code = `(function(){try{
    var t=localStorage.getItem('theme');
    var sys=window.matchMedia('(prefers-color-scheme: dark)').matches;
    var dark=t?t==='dark':sys;
    document.documentElement.classList.toggle('dark', dark);
  }catch(e){}})();`;
  // eslint-disable-next-line react/no-danger
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
