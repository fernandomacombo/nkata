document.addEventListener("DOMContentLoaded", function () {
  const steps = document.querySelectorAll(".form-step");
  const nextButtons = document.querySelectorAll("[data-next]");
  const prevButtons = document.querySelectorAll("[data-prev]");
  const progressItems = document.querySelectorAll(".progress-item");

  let currentStep = 0;

  function showStep(index) {
    steps.forEach((step, stepIndex) => {
      step.classList.toggle("active", stepIndex === index);
    });

    progressItems.forEach((item, itemIndex) => {
      item.classList.toggle("active", itemIndex === index);
      item.classList.toggle("done", itemIndex < index);
    });

    currentStep = index;

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  function validateCurrentStep() {
    const currentPanel = steps[currentStep];
    const fields = currentPanel.querySelectorAll("input, select, textarea");

    for (const field of fields) {
      if (!field.checkValidity()) {
        field.reportValidity();
        return false;
      }
    }

    return true;
  }

  nextButtons.forEach((button) => {
    button.addEventListener("click", function () {
      if (!validateCurrentStep()) {
        return;
      }

      if (currentStep < steps.length - 1) {
        showStep(currentStep + 1);
      }
    });
  });

  prevButtons.forEach((button) => {
    button.addEventListener("click", function () {
      if (currentStep > 0) {
        showStep(currentStep - 1);
      }
    });
  });

  showStep(currentStep);
});