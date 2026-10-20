// Small helpers for the admin pages. Loaded once in <head>; everything listens on `document`, so it keeps
// working after htmx swaps the page body (hx-boost) without any re-binding.
(function () {
  var phone = window.matchMedia("(max-width: 860px)");
  var YEAR = 31536000;

  function setCookie(name, value) {
    document.cookie = name + "=" + value + ";path=/;max-age=" + YEAR + ";samesite=lax";
  }

  function systemDark() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  document.addEventListener("click", function (event) {
    // Sidebar button: on a phone it opens the drawer, on a wide screen it collapses to icons. The choice is
    // kept in a cookie so the server draws the same layout on the next page.
    if (event.target.closest("[data-menu-toggle]")) {
      if (phone.matches) {
        document.body.classList.toggle("menu-open");
      } else {
        var collapsed = document.body.classList.toggle("sidebar-collapsed");
        setCookie("sidebar", collapsed ? "collapsed" : "open");
      }
      return;
    }

    // Light / dark. The theme is written on <html> at once and in a cookie for the next page.
    if (event.target.closest("[data-theme-toggle]")) {
      var root = document.documentElement;
      var current = root.getAttribute("data-theme") || (systemDark() ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      setCookie("theme", next);
      return;
    }

    // Pop-up menus (the create menu, the account menu) close when you click anywhere else.
    document.querySelectorAll("details.menu[open]").forEach(function (menu) {
      if (!menu.contains(event.target) || event.target.closest(".menu-pop a")) {
        menu.removeAttribute("open");
      }
    });

    if (document.body.classList.contains("menu-open") && event.target.closest(".sidebar nav a")) {
      document.body.classList.remove("menu-open");
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      document.querySelectorAll("details.menu[open]").forEach(function (menu) { menu.removeAttribute("open"); });
      document.body.classList.remove("menu-open");
    }
  });

  // <form data-confirm="Really?"> asks before it is sent.
  document.addEventListener(
    "submit",
    function (event) {
      var message = event.target.getAttribute && event.target.getAttribute("data-confirm");
      if (message && !window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
      }
    },
    true
  );

  // Close the phone drawer and any open pop-up after an htmx page swap.
  document.addEventListener("htmx:afterSwap", function () {
    document.body.classList.remove("menu-open");
    document.querySelectorAll("details.menu[open]").forEach(function (menu) { menu.removeAttribute("open"); });
  });
})();
