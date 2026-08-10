"use client";

import { useEffect } from "react";

/**
 * Vinext's client-side Next Link runtime is currently incompatible with the
 * deployed React runtime. Internal navigations intentionally use a normal
 * browser navigation until that upstream runtime issue is resolved.
 */
export function ForceFullNavigation() {
  useEffect(() => {
    function navigateWithBrowser(event: MouseEvent) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const link = (event.target as Element | null)?.closest<HTMLAnchorElement>("a[href]");
      if (!link || link.target || link.download || link.origin !== window.location.origin) return;

      const destination = new URL(link.href);
      if (destination.pathname === window.location.pathname && destination.search === window.location.search) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      window.location.assign(destination.href);
    }

    document.addEventListener("click", navigateWithBrowser, true);
    return () => document.removeEventListener("click", navigateWithBrowser, true);
  }, []);

  return null;
}
