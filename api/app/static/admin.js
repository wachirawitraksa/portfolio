// Small helpers for the admin pages. Loaded once in <head>; everything listens on `document`, so it keeps
// working after htmx swaps the page body (hx-boost) without any re-binding.
(function () {
  // Phone menu: the burger button opens the sidebar, a click anywhere else (or on a link) closes it.
  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-menu-toggle]");
    if (toggle) {
      document.body.classList.toggle("menu-open");
      return;
    }
    if (document.body.classList.contains("menu-open") && !event.target.closest(".sidebar")) {
      document.body.classList.remove("menu-open");
    }
    if (event.target.closest(".sidebar nav a")) {
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

  // Close the phone menu after an htmx page swap.
  document.addEventListener("htmx:afterSwap", function () {
    document.body.classList.remove("menu-open");
  });
})();
