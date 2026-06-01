function AppFooter({ compact = false }) {
  if (compact) {
    return (
      <footer className="border-t border-white/10 pt-3 text-xs leading-5 text-slate-400">
        <p className="font-semibold text-slate-200">Made by Sridhar M</p>
      </footer>
    );
  }

  return (
    <footer className="relative z-10 mx-auto w-full max-w-5xl border-t border-white/10 px-4 py-5 text-center text-sm font-semibold text-slate-300">
      Made by Sridhar M
    </footer>
  );
}

export default AppFooter;
