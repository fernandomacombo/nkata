function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(";") : [];

  for (let cookie of cookies) {
    cookie = cookie.trim();

    if (cookie.startsWith(name + "=")) {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }

  return null;
}

function showNKToast(message) {
  const toast = document.querySelector("[data-toast]");

  if (!toast) return;

  toast.textContent = message;
  toast.hidden = false;

  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  setTimeout(() => {
    toast.classList.remove("show");

    setTimeout(() => {
      toast.hidden = true;
    }, 250);
  }, 2300);
}

function initNKMenu() {
  const menuButtons = document.querySelectorAll("[data-menu-button]");
  const mobileMenu = document.querySelector("[data-mobile-menu]");
  const menuLinks = document.querySelectorAll("[data-mobile-menu] a");

  if (!menuButtons.length || !mobileMenu) return;

  function setMenuState(isOpen) {
    mobileMenu.classList.toggle("is-open", isOpen);

    menuButtons.forEach((button) => {
      button.setAttribute("aria-expanded", isOpen ? "true" : "false");
      button.classList.toggle("is-active", isOpen);
    });

    document.body.classList.toggle("nk-menu-open", isOpen);
  }

  menuButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();

      const isOpen = !mobileMenu.classList.contains("is-open");
      setMenuState(isOpen);
    });
  });

  menuLinks.forEach((link) => {
    link.addEventListener("click", () => {
      setMenuState(false);
    });
  });

  mobileMenu.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  document.addEventListener("click", () => {
    if (mobileMenu.classList.contains("is-open")) {
      setMenuState(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setMenuState(false);
    }
  });
}

function initProfileActions() {
  const csrftoken = getCookie("csrftoken");
  const actionButtons = document.querySelectorAll("[data-action-url]");

  const countGostos = document.getElementById("countGostos");
  const countSeguidores = document.getElementById("countSeguidores");
  const countInteresses = document.getElementById("countInteresses");

  actionButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const url = button.dataset.actionUrl;

      if (!url) return;

      button.disabled = true;
      button.classList.add("is-loading");

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const contentType = response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
          throw new Error("Para denunciar um perfil, precisa primeiro entrar na sua conta NKATA.");
        }

        const data = await response.json();

        if (!response.ok || !data.ok) {
          throw new Error(data.message || "Não foi possível enviar a denúncia.");
        }

        if (data.ativo) {
          button.classList.add("is-active");
        } else {
          button.classList.remove("is-active");
        }

        if (countGostos && typeof data.total_gostos !== "undefined") {
          countGostos.textContent = data.total_gostos;
        }

        if (countSeguidores && typeof data.total_seguidores !== "undefined") {
          countSeguidores.textContent = data.total_seguidores;
        }

        if (countInteresses && typeof data.total_interesses !== "undefined") {
          countInteresses.textContent = data.total_interesses;
        }

        showNKToast(data.message);
      } catch (error) {
        showNKToast(error.message || "Não foi possível concluir a ação.");
      } finally {
        button.disabled = false;
        button.classList.remove("is-loading");
      }
    });
  });
}

function initProfileMessages() {
  const csrftoken = getCookie("csrftoken");
  const messageButtons = document.querySelectorAll("[data-message-url]");

  messageButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const url = button.dataset.messageUrl;

      if (!url) return;

      button.disabled = true;
      button.classList.add("is-loading");

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
          throw new Error(data.message || "Não foi possível enviar a mensagem.");
        }

        button.classList.add("is-sent");
        showNKToast(data.message);
      } catch (error) {
        showNKToast(error.message || "Não foi possível enviar a mensagem.");
      } finally {
        button.disabled = false;
        button.classList.remove("is-loading");
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initNKMenu();
  initProfileActions();
  initProfileMessages();
  initReportProfile();
});







function initReportProfile() {
  const toggle = document.querySelector("[data-report-toggle]");
  const form = document.querySelector("[data-report-form]");

  if (!toggle || !form) return;

  toggle.addEventListener("click", () => {
    form.hidden = !form.hidden;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const csrftoken = getCookie("csrftoken");
    const url = form.dataset.reportUrl;
    const submitButton = form.querySelector("button[type='submit']");
    const formData = new FormData(form);

    submitButton.disabled = true;
    submitButton.classList.add("is-loading");

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        throw new Error(data.message || "Não foi possível enviar a denúncia.");
      }

      form.reset();
      form.hidden = true;

      showNKToast(data.message);

    } catch (error) {
      showNKToast(error.message || "Não foi possível enviar a denúncia.");
    } finally {
      submitButton.disabled = false;
      submitButton.classList.remove("is-loading");
    }
  });
}