
"use strict";


const API_BASE_URL = window.API_BASE_URL;

document.addEventListener("DOMContentLoaded", () => {
  if (window.matchMedia && window.matchMedia("(pointer:fine)").matches) {
    window.addEventListener(
      "pointermove",
      (event) => {
        document.documentElement.style.setProperty(
          "--mx",
          `${event.clientX}px`,
        );
        document.documentElement.style.setProperty(
          "--my",
          `${event.clientY}px`,
        );
      },
      { passive: true },
    );
  }
  const startModal = document.getElementById("startModal");
  const demoModal = document.getElementById("demoModal");
  const interviewForm = document.getElementById("interviewForm");

  const roleInput = document.getElementById("role");
  const levelInput = document.getElementById("level");
  const difficultyInput = document.getElementById("difficulty");
  const typeInput = document.getElementById("type");

  const startButtons = [
    document.getElementById("startHero"),
    document.getElementById("startTop"),
    document.getElementById("startCta"),
  ].filter(Boolean);

  const demoButton = document.getElementById("demoBtn");
  const loginButton = document.getElementById("loginBtn");
  const menuButton = document.getElementById("menuBtn");

  window.addEventListener("prepline-auth-changed", (event) => {
    const user = event.detail?.user;
    if (!loginButton) return;
    if (user) {
      loginButton.textContent = "Log out";
      loginButton.onclick = async () => {
        await window.preplineSignOut();
        location.reload();
      };
    } else {
      loginButton.textContent = "Log in";
      loginButton.onclick = () => {
        location.href = "auth.html";
      };
    }
  });

  function openModal(modal) {
    if (!modal) return;
    modal.classList.add("open");
    document.body.classList.add("modal-open");
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove("open");

    if (!document.querySelector(".modal.open")) {
      document.body.classList.remove("modal-open");
    }
  }

  startButtons.forEach((button) => {
    button.type = "button";
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openModal(startModal);
    });
  });

  document.querySelectorAll(".role-chip").forEach((chip) => {
    chip.addEventListener("click", (event) => {
      event.preventDefault();
      const role = chip.getAttribute("data-role");
      const level = chip.getAttribute("data-level");
      const type = chip.getAttribute("data-type");
      if (role && roleInput) roleInput.value = role;
      if (level && levelInput) levelInput.value = level;
      if (type && typeInput) typeInput.value = type;
      openModal(startModal);
    });
  });

  if (demoButton) {
    demoButton.type = "button";
    demoButton.addEventListener("click", (event) => {
      event.preventDefault();
      openModal(demoModal);
    });
  }

  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      closeModal(button.closest(".modal"));
    });
  });

  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal(modal);
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      document.querySelectorAll(".modal.open").forEach(closeModal);
    }
  });

  if (menuButton) {
    menuButton.type = "button";
    menuButton.addEventListener("click", () => {
      const links = document.querySelector(".nav-links");
      if (links) links.classList.toggle("mobile-open");
    });
  }

  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const href = link.getAttribute("href");
      if (!href || href === "#") return;

      const target = document.querySelector(href);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });

      const links = document.querySelector(".nav-links");
      if (links) links.classList.remove("mobile-open");
    });
  });

  if (loginButton) {
    loginButton.type = "button";
    loginButton.onclick = () => {
      location.href = "auth.html";
    };
  }

  async function readJson(response) {
    const text = await response.text();
    if (!text) return {};

    try {
      return JSON.parse(text);
    } catch {
      return { detail: text };
    }
  }

  function getId(data, keys = []) {
    const sources = [
      data,
      data?.user,
      data?.interview,
      data?.data,
      data?.data?.user,
      data?.data?.interview,
    ];

    for (const source of sources) {
      if (!source || typeof source !== "object") continue;

      for (const key of ["id", ...keys]) {
        if (source[key]) return source[key];
      }
    }

    return null;
  }

  async function createUser(role, experience) {
    const response = await window.preplineFetch(`${API_BASE_URL}/api/users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      signal: AbortSignal.timeout(15000),
      body: JSON.stringify({
        name: "Candidate",
        email: null,
        target_role: role,
        experience_level: experience,
      }),
    });

    const data = await readJson(response);

    if (!response.ok) {
      const detail =
        data.detail ||
        data.message ||
        data.error?.message ||
        data.error ||
        "Unable to create user.";

      throw new Error(
        typeof detail === "string" ? detail : JSON.stringify(detail),
      );
    }

    const userId = getId(data, ["user_id"]);

    if (!userId) {
      console.error("USER CREATE RESPONSE:", data);
      throw new Error("Backend did not return a user ID.");
    }

    localStorage.setItem("prepline_user_id", userId);
    return userId;
  }

  function normalizeDifficulty(value) {
    const difficulty = String(value || "Balanced")
      .trim()
      .toLowerCase();

    if (
      difficulty === "challenging" ||
      difficulty === "hard" ||
      difficulty === "expert" ||
      difficulty === "advanced"
    ) {
      return "hard";
    }

    if (difficulty === "easy" || difficulty === "beginner") {
      return "easy";
    }

    return "medium";
  }

  function normalizeType(value) {
    const type = String(value || "Mixed")
      .trim()
      .toLowerCase();

    if (type === "technical") return "technical";
    if (type === "hr" || type === "behavioral") return "hr";

    return "mixed";
  }

  async function createInterview({
    userId,
    role,
    difficulty,
    type,
    language,
    communicationContext,
    totalQuestions = 12,
  }) {
    const response = await window.preplineFetch(
      `${API_BASE_URL}/api/interviews`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        signal: AbortSignal.timeout(15000),
        body: JSON.stringify({
          user_id: userId,
          interview_type: normalizeType(type),
          difficulty: normalizeDifficulty(difficulty),
          total_questions: Number(totalQuestions),
          language: language || "english",
          interviewer_style: "neutral",
          communication_context: communicationContext || "neutral",
        }),
      },
    );

    const data = await readJson(response);

    if (!response.ok) {
      console.error("INTERVIEW CREATE RESPONSE:", data);

      const detail =
        data.detail ||
        data.message ||
        data.error ||
        "Unable to create interview.";

      throw new Error(
        typeof detail === "string" ? detail : JSON.stringify(detail),
      );
    }

    const interviewId = getId(data, ["interview_id"]);

    if (!interviewId) {
      console.error("INTERVIEW CREATE RESPONSE:", data);
      throw new Error("Backend did not return an interview ID.");
    }

    localStorage.setItem("prepline_last_interview_id", interviewId);

    localStorage.setItem("prepline_total_questions", String(totalQuestions));

    localStorage.setItem("interviewRole", role);

    localStorage.setItem("interviewDifficulty", difficulty);

    localStorage.setItem(
      "prepline_setup",
      JSON.stringify({
        role,
        level: document.getElementById("level")?.value || "Fresher",
        difficulty,
        type,
        interview_type: normalizeType(type),
        language: document.getElementById("language")?.value || "english",
        communication_context:
          document.getElementById("communicationContext")?.value || "neutral",
        total_questions: Number(totalQuestions),
      }),
    );

    return interviewId;
  }

  if (interviewForm) {
    interviewForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const role = roleInput?.value.trim() || "";
      const level = levelInput?.value || "Fresher";
      const difficulty = difficultyInput?.value || "Balanced";
      const type = typeInput?.value || "Technical";
      const language = document.getElementById("language")?.value || "english";
      const communicationContext =
        document.getElementById("communicationContext")?.value || "neutral";
      const totalQuestions = Number(
        document.getElementById("totalQuestions")?.value || 12,
      );

      if (!role) {
        roleInput?.focus();
        return;
      }

      const submitButton =
        interviewForm.querySelector("button[type='submit']") ||
        interviewForm.querySelector("button");

      const originalText = submitButton?.innerHTML || "Enter interview room →";

      try {
        if (submitButton) {
          submitButton.disabled = true;
          submitButton.textContent = "Creating interview...";
        }

        const userId = await createUser(role, level);

        await createInterview({
          userId,
          role,
          difficulty,
          type,
          language,
          communicationContext,
          totalQuestions,
        });

        window.location.assign("interview.html");
      } catch (error) {
        console.error("PREPLINE START ERROR:", error);

        alert(
          error?.message ||
            "Unable to start interview. Make sure the backend is running.",
        );

        if (submitButton) {
          submitButton.disabled = false;
          submitButton.innerHTML = originalText;
        }
      }
    });
  }
});
